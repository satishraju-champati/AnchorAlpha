"""
Streamlit data loader with S3 integration and caching.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import streamlit as st
from functools import lru_cache
import time

try:
    from ..storage.s3_client import S3DataStorage
    from ..models import Stock
except ImportError:
    from AnchorAlpha.storage.s3_client import S3DataStorage
    from AnchorAlpha.models import Stock

# Import config from the cfg module at project root
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

try:
    from cfg.config import Config
except ImportError:
    # Fallback config for testing
    class Config:
        AWS_REGION = "us-east-1"
        S3_BUCKET = "anchoralpha-data"


logger = logging.getLogger(__name__)


class StreamlitDataLoader:
    """Handles data loading and caching for Streamlit frontend."""
    
    def __init__(self):
        """Initialize data loader with S3 client and caching."""
        self.s3_client = S3DataStorage()
        self._cache_ttl = 300  # 5 minutes cache TTL
        self._last_cache_time = {}
        self._error_state = {}  # Track error states for better user feedback
        self._retry_config = {
            'max_retries': 3,
            'retry_delay': 1.0,
            'backoff_factor': 2.0
        }
        
    @st.cache_data(ttl=300, show_spinner=True)
    def load_latest_momentum_data(_self) -> Optional[Dict[str, Any]]:
        """
        Load the most recent momentum data from S3 with caching.
        
        Returns:
            Latest momentum data or None if unavailable
        """
        try:
            # Get list of available dates with retry logic
            try:
                available_dates = _self._get_available_dates_with_retry()
            except Exception as e:
                logger.error(f"Failed to get available dates: {e}")
                _self._set_error_state("loading_error", str(e))
                return None
            
            if not available_dates:
                logger.warning("No momentum data found in S3")
                _self._set_error_state("no_data", "No momentum data available in storage")
                return None
            
            # Try to load the most recent data with fallback
            for i, date in enumerate(available_dates):
                try:
                    data = _self.s3_client.download_momentum_data(date)
                    if data and _self.s3_client.validate_json_schema(data):
                        logger.info(f"Successfully loaded momentum data for {date}")
                        _self._clear_error_state()
                        return data
                    else:
                        logger.warning(f"Invalid or corrupted data for {date}")
                        if i == 0:  # Only set error for most recent data
                            _self._set_error_state("corrupted_data", f"Latest data ({date}) is corrupted")
                except Exception as date_error:
                    logger.warning(f"Failed to load data for {date}: {date_error}")
                    continue
            
            logger.error("No valid momentum data found")
            _self._set_error_state("no_valid_data", "All available data files are corrupted or invalid")
            return None
            
        except Exception as e:
            logger.error(f"Error loading momentum data: {e}")
            _self._set_error_state("loading_error", str(e))
            return None
    
    @st.cache_data(ttl=300)
    def load_momentum_data_by_date(_self, market_date: str) -> Optional[Dict[str, Any]]:
        """
        Load momentum data for a specific date with caching.
        
        Args:
            market_date: Date in YYYY-MM-DD format
            
        Returns:
            Momentum data for the specified date or None if unavailable
        """
        try:
            data = _self.s3_client.download_momentum_data(market_date)
            
            if data and _self.s3_client.validate_json_schema(data):
                logger.info(f"Successfully loaded momentum data for {market_date}")
                _self._clear_error_state()
                return data
            else:
                logger.warning(f"Invalid or corrupted data for {market_date}")
                _self._set_error_state("corrupted_data", f"Data for {market_date} is corrupted or invalid")
                return None
                
        except Exception as e:
            logger.error(f"Error loading momentum data for {market_date}: {e}")
            _self._set_error_state("date_loading_error", f"Failed to load data for {market_date}: {str(e)}")
            return None
    
    @st.cache_data(ttl=600)  # Longer cache for available dates
    def get_available_dates(_self) -> List[str]:
        """
        Get list of available momentum data dates with caching.
        
        Returns:
            List of available dates in YYYY-MM-DD format
        """
        try:
            dates = _self.s3_client.list_available_dates(limit=30)
            logger.info(f"Found {len(dates)} available data dates")
            _self._clear_error_state()
            return dates
            
        except Exception as e:
            logger.error(f"Error getting available dates: {e}")
            _self._set_error_state("dates_error", f"Failed to retrieve available dates: {str(e)}")
            return []
    
    def transform_data_for_ui(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw S3 data for UI display.
        
        Args:
            raw_data: Raw momentum data from S3
            
        Returns:
            Transformed data optimized for UI display
        """
        if not raw_data or 'tiers' not in raw_data:
            return {}
        
        transformed_data = {
            'metadata': {
                'generated_at': raw_data.get('generated_at'),
                'market_date': raw_data.get('market_date'),
                'data_version': raw_data.get('data_version', '1.0')
            },
            'tiers': {},
            'summary': self._generate_data_summary(raw_data)
        }
        
        # Transform each tier
        for tier_name, tier_data in raw_data['tiers'].items():
            transformed_data['tiers'][tier_name] = self._transform_tier_data(tier_data)
        
        return transformed_data
    
    def _transform_tier_data(self, tier_data: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Transform tier data for UI display."""
        transformed_tier = {
            'timeframes': {},
            'stats': {}
        }
        
        # Transform each timeframe
        for timeframe, stocks in tier_data.items():
            if not stocks:
                continue
                
            # Convert timeframe format (e.g., "7_day" -> "7d")
            display_timeframe = timeframe.replace('_day', 'd')
            
            # Transform stock data
            transformed_stocks = []
            for stock_data in stocks:
                transformed_stock = self._transform_stock_data(stock_data, timeframe)
                if transformed_stock:
                    transformed_stocks.append(transformed_stock)
            
            transformed_tier['timeframes'][display_timeframe] = transformed_stocks
            
            # Calculate tier statistics
            if transformed_stocks:
                transformed_tier['stats'][display_timeframe] = self._calculate_tier_stats(transformed_stocks)
        
        return transformed_tier
    
    def _transform_stock_data(self, stock_data: Dict[str, Any], timeframe: str) -> Optional[Dict[str, Any]]:
        """Transform individual stock data for UI display."""
        try:
            # Extract momentum value for the current timeframe
            momentum_field = f"momentum_{timeframe.replace('_day', 'd')}"
            momentum_value = stock_data.get(momentum_field)
            
            if momentum_value is None:
                return None
            
            # Format momentum as percentage
            momentum_pct = momentum_value * 100
            
            # Format market cap for display
            market_cap = stock_data.get('market_cap', 0)
            market_cap_display = self._format_market_cap(market_cap)
            
            # Format price
            current_price = stock_data.get('current_price', 0)
            price_display = f"${current_price:.2f}"
            
            return {
                'ticker': stock_data.get('ticker', ''),
                'company_name': stock_data.get('company_name', ''),
                'current_price': current_price,
                'price_display': price_display,
                'market_cap': market_cap,
                'market_cap_display': market_cap_display,
                'momentum_value': momentum_value,
                'momentum_pct': momentum_pct,
                'momentum_display': f"{momentum_pct:+.2f}%",
                'ai_summary': stock_data.get('ai_summary', ''),
                'tier': stock_data.get('tier', ''),
                'has_summary': bool(stock_data.get('ai_summary'))
            }
            
        except Exception as e:
            logger.error(f"Error transforming stock data: {e}")
            return None
    
    def _format_market_cap(self, market_cap: int) -> str:
        """Format market cap for display."""
        if market_cap >= 1_000_000_000_000:  # $1T+
            return f"${market_cap / 1_000_000_000_000:.1f}T"
        elif market_cap >= 1_000_000_000:  # $1B+
            return f"${market_cap / 1_000_000_000:.1f}B"
        else:
            return f"${market_cap / 1_000_000:.1f}M"
    
    def _calculate_tier_stats(self, stocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate statistics for a tier."""
        if not stocks:
            return {}
        
        momentum_values = [stock['momentum_value'] for stock in stocks if stock['momentum_value'] is not None]
        
        if not momentum_values:
            return {}
        
        return {
            'count': len(stocks),
            'avg_momentum': sum(momentum_values) / len(momentum_values),
            'max_momentum': max(momentum_values),
            'min_momentum': min(momentum_values),
            'stocks_with_summaries': sum(1 for stock in stocks if stock['has_summary'])
        }
    
    def _generate_data_summary(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics for the entire dataset."""
        summary = {
            'total_stocks': 0,
            'total_tiers': 0,
            'timeframes': [],
            'last_updated': raw_data.get('generated_at'),
            'market_date': raw_data.get('market_date')
        }
        
        if 'tiers' not in raw_data:
            return summary
        
        summary['total_tiers'] = len(raw_data['tiers'])
        
        # Count total stocks and collect timeframes
        timeframes_set = set()
        for tier_data in raw_data['tiers'].values():
            for timeframe, stocks in tier_data.items():
                timeframes_set.add(timeframe.replace('_day', 'd'))
                summary['total_stocks'] += len(stocks)
        
        summary['timeframes'] = sorted(list(timeframes_set), key=lambda x: int(x.replace('d', '')))
        
        return summary
    
    def get_tier_display_name(self, tier_key: str) -> str:
        """Convert tier key to display name."""
        tier_names = {
            '100B_200B': '$100B - $200B',
            '200B_500B': '$200B - $500B',
            '500B_1T': '$500B - $1T',
            '1T_plus': '$1T+'
        }
        return tier_names.get(tier_key, tier_key)
    
    def get_timeframe_display_name(self, timeframe_key: str) -> str:
        """Convert timeframe key to display name."""
        timeframe_names = {
            '7d': '7 Days',
            '30d': '30 Days',
            '60d': '60 Days',
            '90d': '90 Days'
        }
        return timeframe_names.get(timeframe_key, timeframe_key)
    
    def validate_data_freshness(self, data: Dict[str, Any], max_age_hours: int = 48) -> bool:
        """
        Validate that data is fresh enough for display.
        
        Args:
            data: Momentum data to validate
            max_age_hours: Maximum age in hours before data is considered stale
            
        Returns:
            True if data is fresh, False otherwise
        """
        if not data or 'generated_at' not in data:
            return False
        
        try:
            generated_at = datetime.fromisoformat(data['generated_at'].replace('Z', '+00:00'))
            age = datetime.now(generated_at.tzinfo) - generated_at
            
            is_fresh = age.total_seconds() < (max_age_hours * 3600)
            
            if not is_fresh:
                logger.warning(f"Data is {age.total_seconds() / 3600:.1f} hours old")
            
            return is_fresh
            
        except Exception as e:
            logger.error(f"Error validating data freshness: {e}")
            return False
    
    def handle_data_loading_error(self, error: Exception) -> Dict[str, Any]:
        """
        Handle data loading errors gracefully.
        
        Args:
            error: Exception that occurred during data loading
            
        Returns:
            Error information for UI display
        """
        error_info = {
            'error': True,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'timestamp': datetime.now().isoformat(),
            'suggestions': []
        }
        
        # Provide specific suggestions based on error type
        if 'NoCredentialsError' in str(type(error)):
            error_info['suggestions'].append("Check AWS credentials configuration")
        elif 'ClientError' in str(type(error)):
            error_info['suggestions'].append("Verify S3 bucket permissions")
            error_info['suggestions'].append("Check S3 bucket name and region")
        elif 'ConnectionError' in str(type(error)):
            error_info['suggestions'].append("Check internet connection")
            error_info['suggestions'].append("Verify AWS service availability")
        else:
            error_info['suggestions'].append("Try refreshing the page")
            error_info['suggestions'].append("Contact support if the issue persists")
        
        logger.error(f"Data loading error: {error_info}")
        return error_info
    
    def _get_available_dates_with_retry(self) -> List[str]:
        """Get available dates with retry logic."""
        import time
        
        for attempt in range(self._retry_config['max_retries']):
            try:
                dates = self.s3_client.list_available_dates(limit=10)
                return dates
            except Exception as e:
                if attempt < self._retry_config['max_retries'] - 1:
                    delay = self._retry_config['retry_delay'] * (self._retry_config['backoff_factor'] ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                    time.sleep(delay)
                else:
                    logger.error(f"All retry attempts failed: {e}")
                    raise e
        
        return []
    
    def _set_error_state(self, error_type: str, error_message: str):
        """Set error state for user feedback."""
        self._error_state = {
            'has_error': True,
            'error_type': error_type,
            'error_message': error_message,
            'timestamp': datetime.now().isoformat()
        }
    
    def _clear_error_state(self):
        """Clear error state."""
        self._error_state = {'has_error': False}
    
    def get_error_state(self) -> Dict[str, Any]:
        """Get current error state for UI display."""
        return self._error_state.copy()
    
    def get_loading_progress(self) -> Dict[str, Any]:
        """Get loading progress information."""
        return {
            'is_loading': hasattr(self, '_loading_state') and self._loading_state.get('active', False),
            'current_step': getattr(self, '_loading_state', {}).get('step', ''),
            'progress_pct': getattr(self, '_loading_state', {}).get('progress', 0)
        }
    
    def _set_loading_state(self, step: str, progress: int = 0):
        """Set loading state for progress indicators."""
        if not hasattr(self, '_loading_state'):
            self._loading_state = {}
        
        self._loading_state.update({
            'active': True,
            'step': step,
            'progress': progress,
            'timestamp': datetime.now().isoformat()
        })
    
    def _clear_loading_state(self):
        """Clear loading state."""
        if hasattr(self, '_loading_state'):
            self._loading_state['active'] = False


# Global data loader instance for Streamlit
# NOTE: Do NOT use @st.cache_resource here — it persists for the entire container
# lifetime and prevents the data cache from refreshing with new S3 files.
# The individual methods use @st.cache_data(ttl=300) which handles caching correctly.
def get_data_loader() -> StreamlitDataLoader:
    """Get data loader instance."""
    return StreamlitDataLoader()