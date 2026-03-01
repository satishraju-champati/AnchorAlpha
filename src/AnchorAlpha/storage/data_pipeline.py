"""
Data pipeline utilities for integrating momentum calculations with S3 storage.
"""

import logging
from datetime import datetime, date
from typing import Dict, List, Optional

from .s3_client import S3DataStorage
from ..models import Stock
from ..momentum_engine import MomentumEngine

logger = logging.getLogger(__name__)


class MomentumDataPipeline:
    """Orchestrates momentum calculation and S3 storage operations."""
    
    def __init__(self, s3_storage: Optional[S3DataStorage] = None):
        """
        Initialize the data pipeline.
        
        Args:
            s3_storage: S3DataStorage instance (creates default if None)
        """
        self.s3_storage = s3_storage or S3DataStorage()
        self.momentum_engine = MomentumEngine()
    
    def process_and_store_momentum_data(self, 
                                      stocks: List[Stock], 
                                      market_date: Optional[str] = None) -> bool:
        """
        Process momentum calculations and store results in S3.
        
        Args:
            stocks: List of Stock objects with momentum data
            market_date: Market date (defaults to today)
            
        Returns:
            True if successful, False otherwise
        """
        if not market_date:
            market_date = date.today().strftime("%Y-%m-%d")
        
        try:
            # Organize stocks by tier and timeframe
            organized_data = self._organize_stocks_by_tier_and_timeframe(stocks)
            
            # Upload to S3
            success = self.s3_storage.upload_momentum_data(organized_data, market_date)
            
            if success:
                logger.info(f"Successfully processed and stored momentum data for {market_date}")
                return True
            else:
                logger.error(f"Failed to store momentum data for {market_date}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing momentum data: {e}")
            return False
    
    def retrieve_momentum_data(self, market_date: str) -> Optional[Dict]:
        """
        Retrieve processed momentum data from S3.
        
        Args:
            market_date: Market date to retrieve (YYYY-MM-DD format)
            
        Returns:
            Momentum data dictionary or None if not found
        """
        try:
            data = self.s3_storage.download_momentum_data(market_date)
            if data:
                logger.info(f"Successfully retrieved momentum data for {market_date}")
            else:
                logger.warning(f"No momentum data found for {market_date}")
            return data
            
        except Exception as e:
            logger.error(f"Error retrieving momentum data for {market_date}: {e}")
            return None
    
    def get_available_data_dates(self, limit: int = 30) -> List[str]:
        """
        Get list of available momentum data dates.
        
        Args:
            limit: Maximum number of dates to return
            
        Returns:
            List of available dates in YYYY-MM-DD format
        """
        try:
            dates = self.s3_storage.list_available_dates(limit)
            logger.info(f"Found {len(dates)} available momentum data dates")
            return dates
            
        except Exception as e:
            logger.error(f"Error listing available dates: {e}")
            return []
    
    def _organize_stocks_by_tier_and_timeframe(self, 
                                             stocks: List[Stock]) -> Dict[str, Dict[str, List[Stock]]]:
        """
        Organize stocks by market cap tier and momentum timeframe.
        
        Args:
            stocks: List of Stock objects
            
        Returns:
            Dictionary organized by tier and timeframe
        """
        # Initialize structure
        organized_data = {
            "100B_200B": {"7": [], "30": [], "60": [], "90": []},
            "200B_500B": {"7": [], "30": [], "60": [], "90": []},
            "500B_1T": {"7": [], "30": [], "60": [], "90": []},
            "1T_plus": {"7": [], "30": [], "60": [], "90": []}
        }
        
        # Group stocks by tier
        stocks_by_tier = {}
        for stock in stocks:
            tier = stock.get_tier()
            if tier not in stocks_by_tier:
                stocks_by_tier[tier] = []
            stocks_by_tier[tier].append(stock)
        
        # For each tier and timeframe, get top 20 performers
        timeframes = [7, 30, 60, 90]
        
        for tier, tier_stocks in stocks_by_tier.items():
            for timeframe in timeframes:
                # Filter stocks that have momentum data for this timeframe
                stocks_with_momentum = [
                    stock for stock in tier_stocks 
                    if stock.get_momentum(timeframe) is not None
                ]
                
                # Sort by momentum (descending) and take top 20
                stocks_with_momentum.sort(
                    key=lambda s: (s.get_momentum(timeframe) or -999, s.market_cap), 
                    reverse=True
                )
                
                top_performers = stocks_with_momentum[:20]
                organized_data[tier][str(timeframe)] = top_performers
        
        return organized_data
    
    def validate_stored_data(self, market_date: str) -> bool:
        """
        Validate stored momentum data for a specific date.
        
        Args:
            market_date: Market date to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        try:
            data = self.s3_storage.download_momentum_data(market_date)
            if not data:
                logger.error(f"No data found for {market_date}")
                return False
            
            # Validate schema
            if not self.s3_storage.validate_json_schema(data):
                logger.error(f"Invalid schema for data on {market_date}")
                return False
            
            # Additional validation checks
            if data.get("market_date") != market_date:
                logger.error(f"Market date mismatch in stored data")
                return False
            
            logger.info(f"Data validation passed for {market_date}")
            return True
            
        except Exception as e:
            logger.error(f"Error validating data for {market_date}: {e}")
            return False