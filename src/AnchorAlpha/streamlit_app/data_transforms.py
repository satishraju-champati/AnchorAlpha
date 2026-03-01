"""
Data transformation utilities for Streamlit UI display.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
from datetime import datetime


logger = logging.getLogger(__name__)


class DataTransformer:
    """Handles data transformations for UI display."""
    
    def __init__(self):
        """Initialize data transformer."""
        self.tier_display_names = {
            '100B_200B': '$100B - $200B',
            '200B_500B': '$200B - $500B',
            '500B_1T': '$500B - $1T',
            '1T_plus': '$1T+'
        }
        
        self.timeframe_display_names = {
            '7d': '7 Days',
            '30d': '30 Days',
            '60d': '60 Days',
            '90d': '90 Days'
        }
    
    def create_stock_dataframe(self, 
                              stocks: List[Dict[str, Any]], 
                              timeframe: str) -> pd.DataFrame:
        """
        Create pandas DataFrame from stock data for table display.
        
        Args:
            stocks: List of stock dictionaries
            timeframe: Timeframe for momentum data
            
        Returns:
            Formatted DataFrame for display
        """
        if not stocks:
            return pd.DataFrame()
        
        try:
            # Create base DataFrame
            df_data = []
            for i, stock in enumerate(stocks, 1):
                row = {
                    'Rank': i,
                    'Ticker': stock.get('ticker', ''),
                    'Company': stock.get('company_name', ''),
                    'Price': stock.get('price_display', ''),
                    'Market Cap': stock.get('market_cap_display', ''),
                    'Momentum': stock.get('momentum_display', ''),
                    'Has Summary': '✓' if stock.get('has_summary', False) else '✗'
                }
                df_data.append(row)
            
            df = pd.DataFrame(df_data)
            
            # Set index to rank for better display
            df.set_index('Rank', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error creating stock DataFrame: {e}")
            return pd.DataFrame()
    
    def create_tier_summary_dataframe(self, 
                                    tier_data: Dict[str, Any]) -> pd.DataFrame:
        """
        Create summary DataFrame for a tier across all timeframes.
        
        Args:
            tier_data: Tier data with timeframes and stats
            
        Returns:
            Summary DataFrame
        """
        if not tier_data or 'stats' not in tier_data:
            return pd.DataFrame()
        
        try:
            summary_data = []
            
            for timeframe, stats in tier_data['stats'].items():
                if not stats:
                    continue
                
                row = {
                    'Timeframe': self.timeframe_display_names.get(timeframe, timeframe),
                    'Stocks': stats.get('count', 0),
                    'Avg Momentum': f"{stats.get('avg_momentum', 0) * 100:+.2f}%",
                    'Max Momentum': f"{stats.get('max_momentum', 0) * 100:+.2f}%",
                    'Min Momentum': f"{stats.get('min_momentum', 0) * 100:+.2f}%",
                    'With AI Summary': stats.get('stocks_with_summaries', 0)
                }
                summary_data.append(row)
            
            df = pd.DataFrame(summary_data)
            return df
            
        except Exception as e:
            logger.error(f"Error creating tier summary DataFrame: {e}")
            return pd.DataFrame()
    
    def create_cross_tier_comparison(self, 
                                   transformed_data: Dict[str, Any], 
                                   timeframe: str) -> pd.DataFrame:
        """
        Create comparison DataFrame across all tiers for a specific timeframe.
        
        Args:
            transformed_data: Full transformed data
            timeframe: Timeframe to compare
            
        Returns:
            Cross-tier comparison DataFrame
        """
        if not transformed_data or 'tiers' not in transformed_data:
            return pd.DataFrame()
        
        try:
            comparison_data = []
            
            for tier_key, tier_data in transformed_data['tiers'].items():
                if timeframe not in tier_data.get('stats', {}):
                    continue
                
                stats = tier_data['stats'][timeframe]
                stocks = tier_data['timeframes'].get(timeframe, [])
                
                # Get top performer
                top_performer = stocks[0] if stocks else None
                
                row = {
                    'Tier': self.tier_display_names.get(tier_key, tier_key),
                    'Total Stocks': stats.get('count', 0),
                    'Avg Momentum': f"{stats.get('avg_momentum', 0) * 100:+.2f}%",
                    'Top Performer': top_performer.get('ticker', 'N/A') if top_performer else 'N/A',
                    'Top Momentum': f"{stats.get('max_momentum', 0) * 100:+.2f}%",
                    'With AI Summary': stats.get('stocks_with_summaries', 0)
                }
                comparison_data.append(row)
            
            df = pd.DataFrame(comparison_data)
            
            # Sort by average momentum descending
            if not df.empty and 'Avg Momentum' in df.columns:
                df['_sort_momentum'] = df['Avg Momentum'].str.replace('%', '').str.replace('+', '').astype(float)
                df = df.sort_values('_sort_momentum', ascending=False)
                df = df.drop('_sort_momentum', axis=1)
            
            return df
            
        except Exception as e:
            logger.error(f"Error creating cross-tier comparison: {e}")
            return pd.DataFrame()
    
    def filter_stocks_by_criteria(self, 
                                stocks: List[Dict[str, Any]], 
                                min_momentum: Optional[float] = None,
                                max_momentum: Optional[float] = None,
                                has_summary: Optional[bool] = None,
                                min_market_cap: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Filter stocks based on various criteria.
        
        Args:
            stocks: List of stock dictionaries
            min_momentum: Minimum momentum threshold
            max_momentum: Maximum momentum threshold
            has_summary: Filter by AI summary availability
            min_market_cap: Minimum market cap threshold
            
        Returns:
            Filtered list of stocks
        """
        if not stocks:
            return []
        
        try:
            filtered_stocks = stocks.copy()
            
            # Filter by momentum range
            if min_momentum is not None:
                filtered_stocks = [s for s in filtered_stocks 
                                 if s.get('momentum_value', 0) >= min_momentum]
            
            if max_momentum is not None:
                filtered_stocks = [s for s in filtered_stocks 
                                 if s.get('momentum_value', 0) <= max_momentum]
            
            # Filter by AI summary availability
            if has_summary is not None:
                filtered_stocks = [s for s in filtered_stocks 
                                 if s.get('has_summary', False) == has_summary]
            
            # Filter by market cap
            if min_market_cap is not None:
                filtered_stocks = [s for s in filtered_stocks 
                                 if s.get('market_cap', 0) >= min_market_cap]
            
            logger.debug(f"Filtered {len(stocks)} stocks to {len(filtered_stocks)}")
            return filtered_stocks
            
        except Exception as e:
            logger.error(f"Error filtering stocks: {e}")
            return stocks
    
    def sort_stocks(self, 
                   stocks: List[Dict[str, Any]], 
                   sort_by: str = 'momentum',
                   ascending: bool = False) -> List[Dict[str, Any]]:
        """
        Sort stocks by specified criteria.
        
        Args:
            stocks: List of stock dictionaries
            sort_by: Sort criteria ('momentum', 'market_cap', 'ticker', 'company_name')
            ascending: Sort order
            
        Returns:
            Sorted list of stocks
        """
        if not stocks:
            return []
        
        try:
            sort_key_map = {
                'momentum': lambda x: x.get('momentum_value', 0),
                'market_cap': lambda x: x.get('market_cap', 0),
                'ticker': lambda x: x.get('ticker', ''),
                'company_name': lambda x: x.get('company_name', ''),
                'price': lambda x: x.get('current_price', 0)
            }
            
            if sort_by not in sort_key_map:
                logger.warning(f"Unknown sort criteria: {sort_by}")
                return stocks
            
            sorted_stocks = sorted(stocks, key=sort_key_map[sort_by], reverse=not ascending)
            logger.debug(f"Sorted {len(stocks)} stocks by {sort_by}")
            return sorted_stocks
            
        except Exception as e:
            logger.error(f"Error sorting stocks: {e}")
            return stocks
    
    def calculate_momentum_distribution(self, 
                                      stocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate momentum distribution statistics.
        
        Args:
            stocks: List of stock dictionaries
            
        Returns:
            Distribution statistics
        """
        if not stocks:
            return {}
        
        try:
            momentum_values = [s.get('momentum_value', 0) for s in stocks 
                             if s.get('momentum_value') is not None]
            
            if not momentum_values:
                return {}
            
            momentum_values.sort()
            n = len(momentum_values)
            
            # Calculate percentiles
            percentiles = {}
            for p in [10, 25, 50, 75, 90]:
                idx = int(n * p / 100)
                if idx >= n:
                    idx = n - 1
                percentiles[f'p{p}'] = momentum_values[idx]
            
            distribution = {
                'count': n,
                'mean': sum(momentum_values) / n,
                'median': percentiles['p50'],
                'min': min(momentum_values),
                'max': max(momentum_values),
                'std': self._calculate_std(momentum_values),
                'percentiles': percentiles,
                'positive_count': sum(1 for v in momentum_values if v > 0),
                'negative_count': sum(1 for v in momentum_values if v < 0),
                'zero_count': sum(1 for v in momentum_values if v == 0)
            }
            
            return distribution
            
        except Exception as e:
            logger.error(f"Error calculating momentum distribution: {e}")
            return {}
    
    def _calculate_std(self, values: List[float]) -> float:
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5
    
    def format_data_for_export(self, 
                              stocks: List[Dict[str, Any]], 
                              tier: str,
                              timeframe: str) -> Dict[str, Any]:
        """
        Format data for export (CSV, JSON, etc.).
        
        Args:
            stocks: List of stock dictionaries
            tier: Tier name
            timeframe: Timeframe
            
        Returns:
            Export-ready data structure
        """
        try:
            export_data = {
                'metadata': {
                    'tier': tier,
                    'timeframe': timeframe,
                    'generated_at': datetime.now().isoformat(),
                    'stock_count': len(stocks)
                },
                'stocks': []
            }
            
            for i, stock in enumerate(stocks, 1):
                export_stock = {
                    'rank': i,
                    'ticker': stock.get('ticker', ''),
                    'company_name': stock.get('company_name', ''),
                    'current_price': stock.get('current_price', 0),
                    'market_cap': stock.get('market_cap', 0),
                    'momentum_value': stock.get('momentum_value', 0),
                    'momentum_percentage': stock.get('momentum_pct', 0),  # Use momentum_pct instead of recalculating
                    'has_ai_summary': stock.get('has_summary', False),
                    'ai_summary': stock.get('ai_summary', '') if stock.get('has_summary') else None
                }
                export_data['stocks'].append(export_stock)
            
            return export_data
            
        except Exception as e:
            logger.error(f"Error formatting data for export: {e}")
            return {'metadata': {}, 'stocks': []}
    
    def create_momentum_heatmap_data(self, 
                                   transformed_data: Dict[str, Any]) -> pd.DataFrame:
        """
        Create data for momentum heatmap visualization.
        
        Args:
            transformed_data: Full transformed data
            
        Returns:
            DataFrame suitable for heatmap display
        """
        if not transformed_data or 'tiers' not in transformed_data:
            return pd.DataFrame()
        
        try:
            heatmap_data = []
            
            for tier_key, tier_data in transformed_data['tiers'].items():
                tier_name = self.tier_display_names.get(tier_key, tier_key)
                
                row = {'Tier': tier_name}
                
                for timeframe in ['7d', '30d', '60d', '90d']:
                    if timeframe in tier_data.get('stats', {}):
                        avg_momentum = tier_data['stats'][timeframe].get('avg_momentum', 0)
                        row[self.timeframe_display_names[timeframe]] = avg_momentum * 100
                    else:
                        row[self.timeframe_display_names[timeframe]] = None
                
                heatmap_data.append(row)
            
            df = pd.DataFrame(heatmap_data)
            df.set_index('Tier', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error creating heatmap data: {e}")
            return pd.DataFrame()