"""
Momentum calculation engine for AnchorAlpha screener.

This module provides the core momentum calculation functionality including:
- Multi-timeframe momentum processing
- Market cap tier categorization
- Data validation and error handling
- Top performer identification
"""

from typing import List, Dict, Optional, Tuple
import logging
from dataclasses import dataclass

from .models import Stock, MomentumCalculation

logger = logging.getLogger(__name__)


@dataclass
class HistoricalPriceData:
    """Container for historical price data."""
    ticker: str
    current_price: float
    prices_7d_ago: Optional[float] = None
    prices_30d_ago: Optional[float] = None
    prices_60d_ago: Optional[float] = None
    prices_90d_ago: Optional[float] = None


class MomentumEngine:
    """Core engine for momentum calculations and stock processing."""
    
    # Market cap tier boundaries
    TIER_BOUNDARIES = {
        "100B_200B": (100_000_000_000, 200_000_000_000),
        "200B_500B": (200_000_000_000, 500_000_000_000),
        "500B_1T": (500_000_000_000, 1_000_000_000_000),
        "1T_plus": (1_000_000_000_000, float('inf'))
    }
    
    # Standard momentum time windows
    TIME_WINDOWS = [7, 30, 60, 90]
    
    def __init__(self):
        """Initialize the momentum engine."""
        self.processed_stocks: List[Stock] = []
        self.tier_rankings: Dict[str, Dict[int, List[Stock]]] = {}
    
    def calculate_stock_momentum(
        self, 
        ticker: str,
        company_name: str,
        current_price: float,
        market_cap: int,
        historical_data: HistoricalPriceData
    ) -> Optional[Stock]:
        """
        Calculate momentum for a single stock across all time windows.
        
        Args:
            ticker: Stock ticker symbol
            company_name: Company name
            current_price: Current stock price
            market_cap: Market capitalization in dollars
            historical_data: Historical price data container
            
        Returns:
            Stock object with calculated momentum or None if validation fails
        """
        try:
            # Validate minimum market cap requirement
            if market_cap < 10_000_000_000:  # $10B minimum
                logger.debug(f"Skipping {ticker}: market cap {market_cap} below $10B threshold")
                return None
            
            # Build historical prices dictionary
            historical_prices = {}
            if historical_data.prices_7d_ago is not None:
                historical_prices[7] = historical_data.prices_7d_ago
            if historical_data.prices_30d_ago is not None:
                historical_prices[30] = historical_data.prices_30d_ago
            if historical_data.prices_60d_ago is not None:
                historical_prices[60] = historical_data.prices_60d_ago
            if historical_data.prices_90d_ago is not None:
                historical_prices[90] = historical_data.prices_90d_ago
            
            # Skip if no historical data available
            if not historical_prices:
                logger.debug(f"Skipping {ticker}: no historical price data available")
                return None
            
            # Create momentum calculation object
            momentum_calc = MomentumCalculation(
                ticker=ticker,
                current_price=current_price,
                historical_prices=historical_prices
            )
            
            # Calculate momentum for all available time windows
            momentum_data = momentum_calc.calculate_all_momentum()
            
            # Create stock object with momentum data
            stock = Stock(
                ticker=ticker,
                company_name=company_name,
                current_price=current_price,
                market_cap=market_cap,
                momentum_7d=momentum_data.get(7),
                momentum_30d=momentum_data.get(30),
                momentum_60d=momentum_data.get(60),
                momentum_90d=momentum_data.get(90)
            )
            
            logger.debug(f"Calculated momentum for {ticker}: {momentum_data}")
            return stock
            
        except (ValueError, TypeError) as e:
            logger.error(f"Error calculating momentum for {ticker}: {e}")
            return None
    
    def process_stock_batch(
        self, 
        stock_data: List[Tuple[str, str, float, int, HistoricalPriceData]]
    ) -> List[Stock]:
        """
        Process a batch of stocks and calculate momentum for each.
        
        Args:
            stock_data: List of tuples containing (ticker, company_name, current_price, market_cap, historical_data)
            
        Returns:
            List of Stock objects with calculated momentum
        """
        processed_stocks = []
        
        for ticker, company_name, current_price, market_cap, historical_data in stock_data:
            stock = self.calculate_stock_momentum(
                ticker, company_name, current_price, market_cap, historical_data
            )
            if stock:
                processed_stocks.append(stock)
        
        logger.info(f"Processed {len(processed_stocks)} stocks out of {len(stock_data)} input stocks")
        self.processed_stocks = processed_stocks
        return processed_stocks
    
    def categorize_by_tier(self, stocks: List[Stock]) -> Dict[str, List[Stock]]:
        """
        Categorize stocks by market cap tiers.
        
        Args:
            stocks: List of Stock objects to categorize
            
        Returns:
            Dictionary mapping tier names to lists of stocks
        """
        tier_stocks = {tier: [] for tier in self.TIER_BOUNDARIES.keys()}
        
        for stock in stocks:
            tier = stock.get_tier()
            tier_stocks[tier].append(stock)
        
        # Log tier distribution
        for tier, stock_list in tier_stocks.items():
            logger.info(f"Tier {tier}: {len(stock_list)} stocks")
        
        return tier_stocks
    
    def rank_stocks_by_momentum(
        self, 
        stocks: List[Stock], 
        time_window: int, 
        top_n: int = 20
    ) -> List[Stock]:
        """
        Rank stocks by momentum for a specific time window with enhanced sorting logic.
        
        Args:
            stocks: List of stocks to rank
            time_window: Time window in days (7, 30, 60, 90)
            top_n: Number of top performers to return
            
        Returns:
            List of top N stocks ranked by momentum (descending), with market cap as tiebreaker
        """
        if time_window not in self.TIME_WINDOWS:
            raise ValueError(f"Invalid time window: {time_window}. Must be one of {self.TIME_WINDOWS}")
        
        # Filter stocks that have momentum data for the specified time window
        stocks_with_momentum = [
            stock for stock in stocks 
            if stock.get_momentum(time_window) is not None
        ]
        
        if not stocks_with_momentum:
            logger.warning(f"No stocks with {time_window}-day momentum data")
            return []
        
        # Enhanced sorting: Primary by momentum (descending), secondary by market cap (descending) for ties
        # This ensures consistent ranking when momentum values are equal
        sorted_stocks = sorted(
            stocks_with_momentum,
            key=lambda s: (s.get_momentum(time_window), s.market_cap),
            reverse=True
        )
        
        # Select top N performers, but don't exceed available stocks
        actual_top_n = min(top_n, len(sorted_stocks))
        top_performers = sorted_stocks[:actual_top_n]
        
        logger.info(
            f"Ranked {len(stocks_with_momentum)} stocks for {time_window}-day window, "
            f"returning top {len(top_performers)} performers"
        )
        
        # Log top performer details for debugging
        if top_performers:
            best_momentum = top_performers[0].get_momentum(time_window)
            worst_in_top = top_performers[-1].get_momentum(time_window)
            logger.debug(
                f"Top performer: {top_performers[0].ticker} ({best_momentum:.2%}), "
                f"Worst in top {actual_top_n}: {top_performers[-1].ticker} ({worst_in_top:.2%})"
            )
        
        return top_performers
    
    def get_top_performers_by_tier(
        self, 
        stocks: List[Stock], 
        time_window: int, 
        top_n: int = 20
    ) -> Dict[str, List[Stock]]:
        """
        Get top N performers for each market cap tier for a specific time window.
        
        Args:
            stocks: List of stocks to process
            time_window: Time window in days (7, 30, 60, 90)
            top_n: Number of top performers per tier
            
        Returns:
            Dictionary mapping tier names to lists of top performing stocks
        """
        if time_window not in self.TIME_WINDOWS:
            raise ValueError(f"Invalid time window: {time_window}. Must be one of {self.TIME_WINDOWS}")
        
        # Categorize stocks by tier
        tier_stocks = self.categorize_by_tier(stocks)
        
        # Get top performers for each tier
        tier_top_performers = {}
        
        for tier, tier_stock_list in tier_stocks.items():
            top_performers = self.rank_stocks_by_momentum(tier_stock_list, time_window, top_n)
            tier_top_performers[tier] = top_performers
            
            logger.info(f"Tier {tier}, {time_window}d window: {len(top_performers)} top performers")
        
        return tier_top_performers
    
    def get_comprehensive_rankings(
        self, 
        stocks: List[Stock], 
        top_n: int = 20
    ) -> Dict[str, Dict[int, List[Stock]]]:
        """
        Generate comprehensive rankings for all tiers and time windows.
        
        This method creates a complete ranking structure that organizes stocks by:
        - Market cap tier (100B-200B, 200B-500B, 500B-1T, 1T+)
        - Time window (7, 30, 60, 90 days)
        - Momentum ranking within each tier/timeframe combination
        
        Args:
            stocks: List of stocks to process
            top_n: Number of top performers per tier/timeframe
            
        Returns:
            Nested dictionary: {tier: {time_window: [ranked_stocks]}}
        """
        logger.info(f"Generating comprehensive rankings for {len(stocks)} stocks")
        
        # Initialize results structure
        comprehensive_rankings = {
            tier: {window: [] for window in self.TIME_WINDOWS}
            for tier in self.TIER_BOUNDARIES.keys()
        }
        
        # Categorize stocks by tier first
        tier_stocks = self.categorize_by_tier(stocks)
        
        # Generate rankings for each tier and time window combination
        total_rankings = 0
        for tier, tier_stock_list in tier_stocks.items():
            if not tier_stock_list:
                logger.debug(f"No stocks in tier {tier}")
                continue
                
            for time_window in self.TIME_WINDOWS:
                top_performers = self.rank_stocks_by_momentum(
                    tier_stock_list, time_window, top_n
                )
                comprehensive_rankings[tier][time_window] = top_performers
                total_rankings += len(top_performers)
                
                if top_performers:
                    best_momentum = top_performers[0].get_momentum(time_window)
                    logger.debug(
                        f"Tier {tier}, {time_window}d: {len(top_performers)} stocks, "
                        f"best momentum: {best_momentum:.2%}"
                    )
        
        logger.info(f"Generated {total_rankings} total rankings across all tiers and timeframes")
        
        # Store results for later access
        self.tier_rankings = comprehensive_rankings
        return comprehensive_rankings
    
    def generate_tier_rankings(
        self, 
        stocks: List[Stock], 
        top_n: int = 20
    ) -> Dict[str, Dict[int, List[Stock]]]:
        """
        Generate complete tier-based rankings for all time windows.
        
        This method is maintained for backward compatibility but now delegates
        to the more comprehensive get_comprehensive_rankings method.
        
        Args:
            stocks: List of stocks to process
            top_n: Number of top performers per tier/timeframe
            
        Returns:
            Nested dictionary: {tier: {time_window: [top_stocks]}}
        """
        return self.get_comprehensive_rankings(stocks, top_n)
    
    def validate_momentum_data(self, stocks: List[Stock]) -> Dict[str, int]:
        """
        Validate momentum data quality and return statistics.
        
        Args:
            stocks: List of stocks to validate
            
        Returns:
            Dictionary with validation statistics
        """
        stats = {
            "total_stocks": len(stocks),
            "stocks_with_7d": 0,
            "stocks_with_30d": 0,
            "stocks_with_60d": 0,
            "stocks_with_90d": 0,
            "stocks_with_all_windows": 0,
            "extreme_momentum_count": 0
        }
        
        for stock in stocks:
            # Count stocks with data for each time window
            if stock.momentum_7d is not None:
                stats["stocks_with_7d"] += 1
            if stock.momentum_30d is not None:
                stats["stocks_with_30d"] += 1
            if stock.momentum_60d is not None:
                stats["stocks_with_60d"] += 1
            if stock.momentum_90d is not None:
                stats["stocks_with_90d"] += 1
            
            # Count stocks with all time windows
            if all(stock.get_momentum(window) is not None for window in self.TIME_WINDOWS):
                stats["stocks_with_all_windows"] += 1
            
            # Count extreme momentum values (>100% or <-50%)
            for window in self.TIME_WINDOWS:
                momentum = stock.get_momentum(window)
                if momentum is not None and (momentum > 1.0 or momentum < -0.5):
                    stats["extreme_momentum_count"] += 1
                    break  # Count each stock only once
        
        logger.info(f"Momentum data validation: {stats}")
        return stats
    
    def get_ranking_summary(self, rankings: Dict[str, Dict[int, List[Stock]]]) -> Dict[str, any]:
        """
        Generate a summary of ranking results for analysis and reporting.
        
        Args:
            rankings: Comprehensive rankings from get_comprehensive_rankings
            
        Returns:
            Dictionary with summary statistics
        """
        summary = {
            "total_tiers": len(rankings),
            "time_windows": self.TIME_WINDOWS.copy(),
            "tier_stats": {},
            "overall_stats": {
                "total_ranked_stocks": 0,
                "stocks_per_timeframe": {},
                "best_performers": {}
            }
        }
        
        # Analyze each tier
        for tier, tier_rankings in rankings.items():
            tier_summary = {
                "total_stocks_across_timeframes": 0,
                "timeframe_counts": {},
                "best_momentum_by_timeframe": {}
            }
            
            for time_window, stocks in tier_rankings.items():
                count = len(stocks)
                tier_summary["timeframe_counts"][time_window] = count
                tier_summary["total_stocks_across_timeframes"] += count
                
                # Track best momentum for this tier/timeframe
                if stocks:
                    best_momentum = stocks[0].get_momentum(time_window)
                    tier_summary["best_momentum_by_timeframe"][time_window] = best_momentum
                    
                    # Track overall best performers
                    if time_window not in summary["overall_stats"]["best_performers"]:
                        summary["overall_stats"]["best_performers"][time_window] = []
                    
                    summary["overall_stats"]["best_performers"][time_window].append({
                        "tier": tier,
                        "ticker": stocks[0].ticker,
                        "momentum": best_momentum
                    })
            
            summary["tier_stats"][tier] = tier_summary
            summary["overall_stats"]["total_ranked_stocks"] += tier_summary["total_stocks_across_timeframes"]
        
        # Calculate stocks per timeframe across all tiers
        for time_window in self.TIME_WINDOWS:
            total_for_timeframe = sum(
                rankings[tier][time_window].__len__() 
                for tier in rankings.keys()
            )
            summary["overall_stats"]["stocks_per_timeframe"][time_window] = total_for_timeframe
        
        # Sort best performers by momentum for each timeframe
        for time_window in summary["overall_stats"]["best_performers"]:
            summary["overall_stats"]["best_performers"][time_window].sort(
                key=lambda x: x["momentum"], reverse=True
            )
        
        logger.info(f"Ranking summary: {summary['overall_stats']['total_ranked_stocks']} total ranked stocks")
        return summary
    
    def find_cross_timeframe_leaders(
        self, 
        rankings: Dict[str, Dict[int, List[Stock]]], 
        min_timeframes: int = 3
    ) -> Dict[str, List[Dict[str, any]]]:
        """
        Identify stocks that appear as top performers across multiple timeframes within their tier.
        
        Args:
            rankings: Comprehensive rankings from get_comprehensive_rankings
            min_timeframes: Minimum number of timeframes a stock must appear in to be considered a leader
            
        Returns:
            Dictionary mapping tier names to lists of cross-timeframe leaders
        """
        cross_timeframe_leaders = {}
        
        for tier, tier_rankings in rankings.items():
            # Track how many timeframes each stock appears in as a top performer
            stock_appearances = {}
            
            for time_window, stocks in tier_rankings.items():
                for stock in stocks:
                    if stock.ticker not in stock_appearances:
                        stock_appearances[stock.ticker] = {
                            "stock": stock,
                            "timeframes": [],
                            "momentum_data": {}
                        }
                    
                    stock_appearances[stock.ticker]["timeframes"].append(time_window)
                    stock_appearances[stock.ticker]["momentum_data"][time_window] = stock.get_momentum(time_window)
            
            # Filter for stocks appearing in minimum number of timeframes
            leaders = []
            for ticker, data in stock_appearances.items():
                if len(data["timeframes"]) >= min_timeframes:
                    # Calculate average momentum across timeframes
                    momentum_values = [v for v in data["momentum_data"].values() if v is not None]
                    avg_momentum = sum(momentum_values) / len(momentum_values) if momentum_values else 0
                    
                    leaders.append({
                        "ticker": ticker,
                        "stock": data["stock"],
                        "timeframes_count": len(data["timeframes"]),
                        "timeframes": sorted(data["timeframes"]),
                        "momentum_data": data["momentum_data"],
                        "average_momentum": avg_momentum
                    })
            
            # Sort leaders by average momentum (descending)
            leaders.sort(key=lambda x: x["average_momentum"], reverse=True)
            cross_timeframe_leaders[tier] = leaders
            
            logger.info(f"Tier {tier}: {len(leaders)} cross-timeframe leaders (min {min_timeframes} timeframes)")
        
        return cross_timeframe_leaders