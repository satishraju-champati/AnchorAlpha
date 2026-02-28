"""
Unit tests for momentum calculation engine.
"""

import pytest
from unittest.mock import patch, MagicMock
import logging

from AnchorAlpha.momentum_engine import MomentumEngine, HistoricalPriceData
from AnchorAlpha.models import Stock, MomentumCalculation


class TestHistoricalPriceData:
    """Test HistoricalPriceData dataclass."""
    
    def test_historical_price_data_creation(self):
        """Test creating HistoricalPriceData object."""
        data = HistoricalPriceData(
            ticker="AAPL",
            current_price=150.0,
            prices_7d_ago=145.0,
            prices_30d_ago=140.0
        )
        
        assert data.ticker == "AAPL"
        assert data.current_price == 150.0
        assert data.prices_7d_ago == 145.0
        assert data.prices_30d_ago == 140.0
        assert data.prices_60d_ago is None
        assert data.prices_90d_ago is None


class TestMomentumEngine:
    """Test MomentumEngine class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = MomentumEngine()
    
    def test_momentum_engine_initialization(self):
        """Test MomentumEngine initialization."""
        assert self.engine.processed_stocks == []
        assert self.engine.tier_rankings == {}
        assert self.engine.TIME_WINDOWS == [7, 30, 60, 90]
        assert len(self.engine.TIER_BOUNDARIES) == 4
    
    def test_tier_boundaries(self):
        """Test tier boundary definitions."""
        boundaries = self.engine.TIER_BOUNDARIES
        
        assert boundaries["100B_200B"] == (100_000_000_000, 200_000_000_000)
        assert boundaries["200B_500B"] == (200_000_000_000, 500_000_000_000)
        assert boundaries["500B_1T"] == (500_000_000_000, 1_000_000_000_000)
        assert boundaries["1T_plus"] == (1_000_000_000_000, float('inf'))
    
    def test_calculate_stock_momentum_success(self):
        """Test successful momentum calculation for a stock."""
        historical_data = HistoricalPriceData(
            ticker="AAPL",
            current_price=150.0,
            prices_7d_ago=145.0,
            prices_30d_ago=140.0,
            prices_60d_ago=135.0,
            prices_90d_ago=130.0
        )
        
        stock = self.engine.calculate_stock_momentum(
            ticker="AAPL",
            company_name="Apple Inc.",
            current_price=150.0,
            market_cap=2_500_000_000_000,  # $2.5T
            historical_data=historical_data
        )
        
        assert stock is not None
        assert stock.ticker == "AAPL"
        assert stock.company_name == "Apple Inc."
        assert stock.current_price == 150.0
        assert stock.market_cap == 2_500_000_000_000
        
        # Check momentum calculations
        assert abs(stock.momentum_7d - (150.0/145.0 - 1)) < 0.0001  # ~3.45%
        assert abs(stock.momentum_30d - (150.0/140.0 - 1)) < 0.0001  # ~7.14%
        assert abs(stock.momentum_60d - (150.0/135.0 - 1)) < 0.0001  # ~11.11%
        assert abs(stock.momentum_90d - (150.0/130.0 - 1)) < 0.0001  # ~15.38%
    
    def test_calculate_stock_momentum_below_market_cap_threshold(self):
        """Test stock rejection due to low market cap."""
        historical_data = HistoricalPriceData(
            ticker="SMALL",
            current_price=10.0,
            prices_7d_ago=9.5
        )
        
        stock = self.engine.calculate_stock_momentum(
            ticker="SMALL",
            company_name="Small Corp",
            current_price=10.0,
            market_cap=5_000_000_000,  # $5B - below threshold
            historical_data=historical_data
        )
        
        assert stock is None
    
    def test_calculate_stock_momentum_no_historical_data(self):
        """Test stock rejection due to no historical data."""
        historical_data = HistoricalPriceData(
            ticker="NODATA",
            current_price=100.0
            # No historical prices
        )
        
        stock = self.engine.calculate_stock_momentum(
            ticker="NODATA",
            company_name="No Data Corp",
            current_price=100.0,
            market_cap=50_000_000_000,  # $50B
            historical_data=historical_data
        )
        
        assert stock is None
    
    def test_calculate_stock_momentum_partial_historical_data(self):
        """Test momentum calculation with partial historical data."""
        historical_data = HistoricalPriceData(
            ticker="PARTIAL",
            current_price=100.0,
            prices_7d_ago=95.0,
            prices_30d_ago=90.0
            # Missing 60d and 90d data
        )
        
        stock = self.engine.calculate_stock_momentum(
            ticker="PARTIAL",
            company_name="Partial Data Corp",
            current_price=100.0,
            market_cap=150_000_000_000,  # $150B
            historical_data=historical_data
        )
        
        assert stock is not None
        assert stock.momentum_7d is not None
        assert stock.momentum_30d is not None
        assert stock.momentum_60d is None
        assert stock.momentum_90d is None
    
    def test_calculate_stock_momentum_invalid_data(self):
        """Test error handling for invalid data."""
        historical_data = HistoricalPriceData(
            ticker="INVALID",
            current_price=-10.0,  # Invalid negative price
            prices_7d_ago=95.0
        )
        
        stock = self.engine.calculate_stock_momentum(
            ticker="INVALID",
            company_name="Invalid Corp",
            current_price=-10.0,
            market_cap=150_000_000_000,
            historical_data=historical_data
        )
        
        assert stock is None
    
    def test_process_stock_batch(self):
        """Test processing a batch of stocks."""
        stock_data = [
            ("AAPL", "Apple Inc.", 150.0, 2_500_000_000_000, 
             HistoricalPriceData("AAPL", 150.0, 145.0, 140.0)),
            ("MSFT", "Microsoft Corp.", 300.0, 2_200_000_000_000,
             HistoricalPriceData("MSFT", 300.0, 295.0, 290.0)),
            ("SMALL", "Small Corp", 10.0, 5_000_000_000,  # Below threshold
             HistoricalPriceData("SMALL", 10.0, 9.5))
        ]
        
        processed_stocks = self.engine.process_stock_batch(stock_data)
        
        assert len(processed_stocks) == 2  # SMALL should be filtered out
        assert processed_stocks[0].ticker in ["AAPL", "MSFT"]
        assert processed_stocks[1].ticker in ["AAPL", "MSFT"]
        assert self.engine.processed_stocks == processed_stocks
    
    def test_categorize_by_tier(self):
        """Test stock categorization by market cap tiers."""
        stocks = [
            Stock("AAPL", "Apple Inc.", 150.0, 2_500_000_000_000),  # 1T+
            Stock("GOOGL", "Alphabet Inc.", 2500.0, 1_600_000_000_000),  # 1T+
            Stock("NVDA", "NVIDIA Corp.", 800.0, 800_000_000_000),  # 500B-1T
            Stock("TSLA", "Tesla Inc.", 200.0, 600_000_000_000),  # 500B-1T
            Stock("META", "Meta Platforms", 300.0, 750_000_000_000),  # 500B-1T
            Stock("BRK.A", "Berkshire Hathaway", 500000.0, 400_000_000_000),  # 200B-500B
            Stock("UNH", "UnitedHealth Group", 500.0, 450_000_000_000),  # 200B-500B
            Stock("JNJ", "Johnson & Johnson", 160.0, 420_000_000_000),  # 200B-500B
            Stock("V", "Visa Inc.", 250.0, 180_000_000_000),  # 100B-200B
            Stock("PG", "Procter & Gamble", 150.0, 350_000_000_000),  # 200B-500B
            Stock("HD", "Home Depot", 300.0, 320_000_000_000),  # 200B-500B
            Stock("MA", "Mastercard Inc.", 400.0, 380_000_000_000),  # 200B-500B
            Stock("ABBV", "AbbVie Inc.", 140.0, 250_000_000_000),  # 200B-500B
            Stock("PFE", "Pfizer Inc.", 35.0, 200_000_000_000),  # 200B-500B
            Stock("KO", "Coca-Cola Co.", 60.0, 260_000_000_000),  # 200B-500B
            Stock("PEP", "PepsiCo Inc.", 170.0, 240_000_000_000),  # 200B-500B
            Stock("COST", "Costco Wholesale", 500.0, 220_000_000_000),  # 200B-500B
            Stock("AVGO", "Broadcom Inc.", 900.0, 380_000_000_000),  # 200B-500B
            Stock("WMT", "Walmart Inc.", 150.0, 410_000_000_000),  # 200B-500B
            Stock("LLY", "Eli Lilly and Co.", 600.0, 570_000_000_000),  # 500B-1T
            Stock("XOM", "Exxon Mobil Corp.", 100.0, 420_000_000_000),  # 200B-500B
            Stock("ADBE", "Adobe Inc.", 500.0, 230_000_000_000),  # 200B-500B
            Stock("NFLX", "Netflix Inc.", 400.0, 180_000_000_000),  # 100B-200B
            Stock("CRM", "Salesforce Inc.", 200.0, 190_000_000_000),  # 100B-200B
            Stock("ORCL", "Oracle Corp.", 100.0, 280_000_000_000),  # 200B-500B
            Stock("ACN", "Accenture plc", 300.0, 190_000_000_000),  # 100B-200B
            Stock("AMD", "Advanced Micro Devices", 100.0, 160_000_000_000),  # 100B-200B
            Stock("CSCO", "Cisco Systems Inc.", 50.0, 200_000_000_000),  # 200B-500B
            Stock("INTC", "Intel Corp.", 30.0, 120_000_000_000),  # 100B-200B
            Stock("IBM", "International Business Machines", 140.0, 130_000_000_000),  # 100B-200B
            Stock("QCOM", "QUALCOMM Inc.", 150.0, 170_000_000_000),  # 100B-200B
            Stock("TXN", "Texas Instruments Inc.", 170.0, 150_000_000_000),  # 100B-200B
            Stock("HON", "Honeywell International Inc.", 200.0, 140_000_000_000),  # 100B-200B
            Stock("UPS", "United Parcel Service Inc.", 150.0, 130_000_000_000),  # 100B-200B
            Stock("LOW", "Lowe's Companies Inc.", 200.0, 130_000_000_000),  # 100B-200B
            Stock("CAT", "Caterpillar Inc.", 250.0, 140_000_000_000),  # 100B-200B
            Stock("GS", "Goldman Sachs Group Inc.", 350.0, 120_000_000_000),  # 100B-200B
            Stock("MS", "Morgan Stanley", 90.0, 150_000_000_000),  # 100B-200B
            Stock("AXP", "American Express Co.", 150.0, 110_000_000_000),  # 100B-200B
            Stock("BA", "Boeing Co.", 200.0, 120_000_000_000),  # 100B-200B
            Stock("MMM", "3M Co.", 100.0, 110_000_000_000),  # 100B-200B
            Stock("GE", "General Electric Co.", 100.0, 110_000_000_000),  # 100B-200B
            Stock("AMGN", "Amgen Inc.", 250.0, 140_000_000_000),  # 100B-200B
            Stock("SBUX", "Starbucks Corp.", 100.0, 110_000_000_000),  # 100B-200B
            Stock("MDLZ", "Mondelez International Inc.", 70.0, 100_000_000_000),  # 100B-200B
            Stock("GILD", "Gilead Sciences Inc.", 70.0, 110_000_000_000),  # 100B-200B
            Stock("BKNG", "Booking Holdings Inc.", 3000.0, 120_000_000_000),  # 100B-200B
            Stock("ISRG", "Intuitive Surgical Inc.", 300.0, 110_000_000_000),  # 100B-200B
            Stock("MU", "Micron Technology Inc.", 80.0, 90_000_000_000),  # Below 100B threshold - should not be included
            Stock("AMAT", "Applied Materials Inc.", 150.0, 130_000_000_000),  # 100B-200B
            Stock("ADI", "Analog Devices Inc.", 200.0, 100_000_000_000),  # 100B-200B
        ]
        
        tier_stocks = self.engine.categorize_by_tier(stocks)
        
        # Check that all tiers are present
        assert set(tier_stocks.keys()) == {"100B_200B", "200B_500B", "500B_1T", "1T_plus"}
        
        # Check 1T+ tier
        assert len(tier_stocks["1T_plus"]) == 2  # AAPL, GOOGL
        
        # Check 500B-1T tier  
        assert len(tier_stocks["500B_1T"]) == 4  # NVDA, TSLA, META, LLY
        
        # Check 200B-500B tier
        assert len(tier_stocks["200B_500B"]) >= 10  # Multiple stocks in this range
        
        # Check 100B-200B tier
        assert len(tier_stocks["100B_200B"]) >= 15  # Multiple stocks in this range
    
    def test_rank_stocks_by_momentum_enhanced(self):
        """Test enhanced ranking with improved logging and edge cases."""
        stocks = [
            Stock("HIGH", "High Momentum", 100.0, 500_000_000_000, momentum_7d=0.15),  # 15%
            Stock("MED", "Medium Momentum", 100.0, 400_000_000_000, momentum_7d=0.10),  # 10%
            Stock("LOW", "Low Momentum", 100.0, 600_000_000_000, momentum_7d=0.05),   # 5%
            Stock("NEG", "Negative Momentum", 100.0, 300_000_000_000, momentum_7d=-0.05), # -5%
            Stock("NONE", "No Data", 100.0, 200_000_000_000)  # No momentum data
        ]
        
        # Test with top_n larger than available stocks
        ranked = self.engine.rank_stocks_by_momentum(stocks, 7, top_n=10)
        
        assert len(ranked) == 4  # NONE should be excluded
        assert ranked[0].ticker == "HIGH"  # Highest momentum
        assert ranked[1].ticker == "MED"
        assert ranked[2].ticker == "LOW"
        assert ranked[3].ticker == "NEG"  # Lowest momentum
        
        # Test with top_n smaller than available stocks
        ranked_limited = self.engine.rank_stocks_by_momentum(stocks, 7, top_n=2)
        assert len(ranked_limited) == 2
        assert ranked_limited[0].ticker == "HIGH"
        assert ranked_limited[1].ticker == "MED"
    
    def test_get_top_performers_by_tier(self):
        """Test getting top performers organized by tier."""
        stocks = [
            # 1T+ tier
            Stock("AAPL", "Apple", 150.0, 2_500_000_000_000, momentum_7d=0.05),
            Stock("MSFT", "Microsoft", 300.0, 2_200_000_000_000, momentum_7d=0.08),
            
            # 500B-1T tier
            Stock("NVDA", "NVIDIA", 800.0, 800_000_000_000, momentum_7d=0.12),
            Stock("TSLA", "Tesla", 200.0, 600_000_000_000, momentum_7d=0.10),
            
            # 200B-500B tier
            Stock("META", "Meta", 300.0, 400_000_000_000, momentum_7d=0.15),
            
            # 100B-200B tier
            Stock("NFLX", "Netflix", 400.0, 180_000_000_000, momentum_7d=0.20),
        ]
        
        tier_performers = self.engine.get_top_performers_by_tier(stocks, 7, top_n=2)
        
        # Check structure
        assert "1T_plus" in tier_performers
        assert "500B_1T" in tier_performers
        assert "200B_500B" in tier_performers
        assert "100B_200B" in tier_performers
        
        # Check 1T+ tier (should have MSFT first due to higher momentum)
        assert len(tier_performers["1T_plus"]) == 2
        assert tier_performers["1T_plus"][0].ticker == "MSFT"
        assert tier_performers["1T_plus"][1].ticker == "AAPL"
        
        # Check 500B-1T tier (should have NVDA first)
        assert len(tier_performers["500B_1T"]) == 2
        assert tier_performers["500B_1T"][0].ticker == "NVDA"
        
        # Check other tiers
        assert len(tier_performers["200B_500B"]) == 1
        assert tier_performers["200B_500B"][0].ticker == "META"
        
        assert len(tier_performers["100B_200B"]) == 1
        assert tier_performers["100B_200B"][0].ticker == "NFLX"
    
    def test_get_comprehensive_rankings(self):
        """Test comprehensive rankings generation."""
        stocks = [
            # 1T+ tier with full momentum data
            Stock("AAPL", "Apple", 150.0, 2_500_000_000_000, 
                  momentum_7d=0.05, momentum_30d=0.10, momentum_60d=0.15, momentum_90d=0.20),
            Stock("MSFT", "Microsoft", 300.0, 2_200_000_000_000,
                  momentum_7d=0.03, momentum_30d=0.08, momentum_60d=0.12, momentum_90d=0.18),
            
            # 500B-1T tier
            Stock("NVDA", "NVIDIA", 800.0, 800_000_000_000,
                  momentum_7d=0.08, momentum_30d=0.15, momentum_60d=0.25, momentum_90d=0.35),
        ]
        
        rankings = self.engine.get_comprehensive_rankings(stocks, top_n=2)
        
        # Check structure
        assert len(rankings) == 4  # All tiers present
        for tier in self.engine.TIER_BOUNDARIES.keys():
            assert tier in rankings
            assert len(rankings[tier]) == 4  # All time windows present
            for time_window in self.engine.TIME_WINDOWS:
                assert time_window in rankings[tier]
        
        # Check 1T+ tier rankings for different time windows
        tier_1t = rankings["1T_plus"]
        assert len(tier_1t[7]) == 2  # Both stocks
        assert tier_1t[7][0].ticker == "AAPL"  # Higher 7d momentum
        assert tier_1t[30][0].ticker == "AAPL"  # Higher 30d momentum
        
        # Check that tier_rankings is stored
        assert self.engine.tier_rankings == rankings
    
    def test_get_ranking_summary(self):
        """Test ranking summary generation."""
        stocks = [
            Stock("AAPL", "Apple", 150.0, 2_500_000_000_000, 
                  momentum_7d=0.05, momentum_30d=0.10),
            Stock("NVDA", "NVIDIA", 800.0, 800_000_000_000,
                  momentum_7d=0.08, momentum_30d=0.15),
            Stock("META", "Meta", 300.0, 400_000_000_000,
                  momentum_7d=0.12),  # Only 7d data
        ]
        
        rankings = self.engine.get_comprehensive_rankings(stocks, top_n=5)
        summary = self.engine.get_ranking_summary(rankings)
        
        # Check summary structure
        assert "total_tiers" in summary
        assert "time_windows" in summary
        assert "tier_stats" in summary
        assert "overall_stats" in summary
        
        assert summary["total_tiers"] == 4
        assert summary["time_windows"] == [7, 30, 60, 90]
        
        # Check overall stats
        overall = summary["overall_stats"]
        assert "total_ranked_stocks" in overall
        assert "stocks_per_timeframe" in overall
        assert "best_performers" in overall
        
        # Should have stocks for 7d and 30d timeframes
        assert overall["stocks_per_timeframe"][7] > 0
        assert overall["stocks_per_timeframe"][30] > 0
        assert overall["stocks_per_timeframe"][60] == 0  # No 60d data
        assert overall["stocks_per_timeframe"][90] == 0  # No 90d data
        
        # Check best performers structure
        assert 7 in overall["best_performers"]
        assert 30 in overall["best_performers"]
        
        # Best performer for 7d should be META (highest momentum)
        best_7d = overall["best_performers"][7]
        assert len(best_7d) > 0
        # Find META in the best performers (could be in any tier)
        meta_found = any(perf["ticker"] == "META" for perf in best_7d)
        assert meta_found
    
    def test_find_cross_timeframe_leaders(self):
        """Test identification of cross-timeframe leaders."""
        stocks = [
            # Stock that appears in multiple timeframes
            Stock("LEADER", "Consistent Leader", 150.0, 2_500_000_000_000, 
                  momentum_7d=0.10, momentum_30d=0.12, momentum_60d=0.15, momentum_90d=0.18),
            
            # Stock that appears in fewer timeframes
            Stock("PARTIAL", "Partial Leader", 300.0, 2_200_000_000_000,
                  momentum_7d=0.08, momentum_30d=0.09),  # Only 2 timeframes
            
            # Stock with inconsistent performance
            Stock("INCONSISTENT", "Inconsistent", 800.0, 800_000_000_000,
                  momentum_7d=0.05, momentum_60d=0.20),  # Only 2 timeframes, gaps
        ]
        
        rankings = self.engine.get_comprehensive_rankings(stocks, top_n=5)
        leaders = self.engine.find_cross_timeframe_leaders(rankings, min_timeframes=3)
        
        # Check structure
        for tier in self.engine.TIER_BOUNDARIES.keys():
            assert tier in leaders
        
        # LEADER should appear in 1T+ tier with 4 timeframes
        tier_1t_leaders = leaders["1T_plus"]
        assert len(tier_1t_leaders) == 1  # Only LEADER meets min_timeframes=3
        
        leader_data = tier_1t_leaders[0]
        assert leader_data["ticker"] == "LEADER"
        assert leader_data["timeframes_count"] == 4
        assert leader_data["timeframes"] == [7, 30, 60, 90]
        assert "average_momentum" in leader_data
        assert leader_data["average_momentum"] > 0
        
        # 500B-1T tier should have no leaders (INCONSISTENT only has 2 timeframes)
        tier_500b_leaders = leaders["500B_1T"]
        assert len(tier_500b_leaders) == 0
    
    def test_find_cross_timeframe_leaders_different_thresholds(self):
        """Test cross-timeframe leaders with different minimum thresholds."""
        stocks = [
            Stock("MULTI", "Multi Timeframe", 150.0, 2_500_000_000_000, 
                  momentum_7d=0.10, momentum_30d=0.12, momentum_60d=0.15),  # 3 timeframes
            Stock("DUAL", "Dual Timeframe", 300.0, 2_200_000_000_000,
                  momentum_7d=0.08, momentum_30d=0.09),  # 2 timeframes
        ]
        
        rankings = self.engine.get_comprehensive_rankings(stocks, top_n=5)
        
        # Test with min_timeframes=2
        leaders_2 = self.engine.find_cross_timeframe_leaders(rankings, min_timeframes=2)
        tier_1t_leaders_2 = leaders_2["1T_plus"]
        assert len(tier_1t_leaders_2) == 2  # Both stocks qualify
        
        # Test with min_timeframes=3
        leaders_3 = self.engine.find_cross_timeframe_leaders(rankings, min_timeframes=3)
        tier_1t_leaders_3 = leaders_3["1T_plus"]
        assert len(tier_1t_leaders_3) == 1  # Only MULTI qualifies
        assert tier_1t_leaders_3[0]["ticker"] == "MULTI"
        
        # Test with min_timeframes=4
        leaders_4 = self.engine.find_cross_timeframe_leaders(rankings, min_timeframes=4)
        tier_1t_leaders_4 = leaders_4["1T_plus"]
        assert len(tier_1t_leaders_4) == 0  # No stocks qualify
    
    def test_ranking_edge_cases(self):
        """Test edge cases in ranking functionality."""
        # Test with empty stock list
        empty_rankings = self.engine.get_comprehensive_rankings([], top_n=20)
        assert len(empty_rankings) == 4  # All tiers present but empty
        for tier in empty_rankings.values():
            for time_window_stocks in tier.values():
                assert len(time_window_stocks) == 0
        
        # Test with stocks having no momentum data
        no_momentum_stocks = [
            Stock("NO_DATA_1", "No Data 1", 100.0, 500_000_000_000),
            Stock("NO_DATA_2", "No Data 2", 200.0, 1_500_000_000_000),
        ]
        
        no_momentum_rankings = self.engine.get_comprehensive_rankings(no_momentum_stocks, top_n=20)
        for tier in no_momentum_rankings.values():
            for time_window_stocks in tier.values():
                assert len(time_window_stocks) == 0
    
    def test_ranking_with_extreme_values(self):
        """Test ranking with extreme momentum values."""
        stocks = [
            Stock("EXTREME_HIGH", "Extreme High", 100.0, 500_000_000_000, momentum_7d=5.0),  # 500%
            Stock("EXTREME_LOW", "Extreme Low", 100.0, 400_000_000_000, momentum_7d=-0.8),   # -80%
            Stock("NORMAL", "Normal", 100.0, 600_000_000_000, momentum_7d=0.1),              # 10%
        ]
        
        ranked = self.engine.rank_stocks_by_momentum(stocks, 7)
        
        assert len(ranked) == 3
        assert ranked[0].ticker == "EXTREME_HIGH"  # Highest momentum
        assert ranked[1].ticker == "NORMAL"        # Middle momentum
        assert ranked[2].ticker == "EXTREME_LOW"   # Lowest momentum
    
    def test_tier_boundary_edge_cases(self):
        """Test stocks at tier boundaries."""
        stocks = [
            # Exactly at tier boundaries
            Stock("BOUNDARY_100B", "Boundary 100B", 100.0, 100_000_000_000, momentum_7d=0.05),      # Exactly 100B
            Stock("BOUNDARY_200B", "Boundary 200B", 100.0, 200_000_000_000, momentum_7d=0.06),      # Exactly 200B
            Stock("BOUNDARY_500B", "Boundary 500B", 100.0, 500_000_000_000, momentum_7d=0.07),      # Exactly 500B
            Stock("BOUNDARY_1T", "Boundary 1T", 100.0, 1_000_000_000_000, momentum_7d=0.08),        # Exactly 1T
            
            # Just above boundaries
            Stock("ABOVE_100B", "Above 100B", 100.0, 100_000_000_001, momentum_7d=0.09),            # Just above 100B
            Stock("ABOVE_200B", "Above 200B", 100.0, 200_000_000_001, momentum_7d=0.10),            # Just above 200B
        ]
        
        tier_stocks = self.engine.categorize_by_tier(stocks)
        
        # Check boundary assignments
        assert any(s.ticker == "BOUNDARY_100B" for s in tier_stocks["100B_200B"])
        assert any(s.ticker == "BOUNDARY_200B" for s in tier_stocks["200B_500B"])
        assert any(s.ticker == "BOUNDARY_500B" for s in tier_stocks["500B_1T"])
        assert any(s.ticker == "BOUNDARY_1T" for s in tier_stocks["1T_plus"])
        
        # Check just above boundary assignments
        assert any(s.ticker == "ABOVE_100B" for s in tier_stocks["100B_200B"])
        assert any(s.ticker == "ABOVE_200B" for s in tier_stocks["200B_500B"])
    
    def test_generate_tier_rankings_backward_compatibility(self):
        """Test that generate_tier_rankings maintains backward compatibility."""
        stocks = [
            Stock("AAPL", "Apple", 150.0, 2_500_000_000_000, 
                  momentum_7d=0.05, momentum_30d=0.10),
            Stock("NVDA", "NVIDIA", 800.0, 800_000_000_000,
                  momentum_7d=0.08, momentum_30d=0.15),
        ]
        
        # Test old method
        old_rankings = self.engine.generate_tier_rankings(stocks, top_n=5)
        
        # Test new method
        new_rankings = self.engine.get_comprehensive_rankings(stocks, top_n=5)
        
        # Should produce identical results
        assert old_rankings == new_rankings
        
        # Check that tier_rankings is set
        assert self.engine.tier_rankings == old_rankings
    
    def test_rank_stocks_by_momentum_with_ties(self):
        """Test ranking with tied momentum values (should use market cap as tiebreaker)."""
        stocks = [
            Stock("TIE1", "Tie Small", 100.0, 300_000_000_000, momentum_7d=0.10),
            Stock("TIE2", "Tie Large", 100.0, 500_000_000_000, momentum_7d=0.10),
        ]
        
        ranked = self.engine.rank_stocks_by_momentum(stocks, 7)
        
        assert len(ranked) == 2
        assert ranked[0].ticker == "TIE2"  # Higher market cap should come first
        assert ranked[1].ticker == "TIE1"
    
    def test_rank_stocks_invalid_time_window(self):
        """Test error handling for invalid time window."""
        stocks = [Stock("TEST", "Test", 100.0, 500_000_000_000, momentum_7d=0.10)]
        
        with pytest.raises(ValueError, match="Invalid time window: 14"):
            self.engine.rank_stocks_by_momentum(stocks, 14)
    
    def test_generate_tier_rankings(self):
        """Test generating complete tier rankings."""
        stocks = [
            # 1T+ tier
            Stock("AAPL", "Apple", 150.0, 2_500_000_000_000, 
                  momentum_7d=0.05, momentum_30d=0.10, momentum_60d=0.15, momentum_90d=0.20),
            Stock("MSFT", "Microsoft", 300.0, 2_200_000_000_000,
                  momentum_7d=0.03, momentum_30d=0.08, momentum_60d=0.12, momentum_90d=0.18),
            
            # 500B-1T tier
            Stock("NVDA", "NVIDIA", 800.0, 800_000_000_000,
                  momentum_7d=0.08, momentum_30d=0.15, momentum_60d=0.25, momentum_90d=0.35),
            Stock("TSLA", "Tesla", 200.0, 600_000_000_000,
                  momentum_7d=0.12, momentum_30d=0.20, momentum_60d=0.30, momentum_90d=0.40),
        ]
        
        rankings = self.engine.generate_tier_rankings(stocks, top_n=2)
        
        # Check structure
        assert "1T_plus" in rankings
        assert "500B_1T" in rankings
        assert "200B_500B" in rankings
        assert "100B_200B" in rankings
        
        # Check 1T+ tier rankings
        tier_1t = rankings["1T_plus"]
        assert len(tier_1t[7]) == 2  # Both stocks
        assert tier_1t[7][0].ticker == "AAPL"  # Higher 7d momentum
        assert tier_1t[30][0].ticker == "AAPL"  # Higher 30d momentum
        
        # Check 500B-1T tier rankings
        tier_500b = rankings["500B_1T"]
        assert len(tier_500b[7]) == 2
        assert tier_500b[7][0].ticker == "TSLA"  # Higher 7d momentum
        assert tier_500b[90][0].ticker == "TSLA"  # Higher 90d momentum
    
    def test_validate_momentum_data(self):
        """Test momentum data validation."""
        stocks = [
            Stock("FULL", "Full Data", 100.0, 500_000_000_000,
                  momentum_7d=0.05, momentum_30d=0.10, momentum_60d=0.15, momentum_90d=0.20),
            Stock("PARTIAL", "Partial Data", 100.0, 400_000_000_000,
                  momentum_7d=0.03, momentum_30d=0.08),  # Missing 60d, 90d
            Stock("EXTREME", "Extreme Momentum", 100.0, 300_000_000_000,
                  momentum_7d=1.5),  # 150% momentum - extreme
            Stock("NEGATIVE", "Negative Extreme", 100.0, 200_000_000_000,
                  momentum_7d=-0.6),  # -60% momentum - extreme
        ]
        
        stats = self.engine.validate_momentum_data(stocks)
        
        assert stats["total_stocks"] == 4
        assert stats["stocks_with_7d"] == 4
        assert stats["stocks_with_30d"] == 2
        assert stats["stocks_with_60d"] == 1
        assert stats["stocks_with_90d"] == 1
        assert stats["stocks_with_all_windows"] == 1
        assert stats["extreme_momentum_count"] == 2  # EXTREME and NEGATIVE
    
    @patch('AnchorAlpha.momentum_engine.logger')
    def test_logging_behavior(self, mock_logger):
        """Test that appropriate logging occurs."""
        historical_data = HistoricalPriceData(
            ticker="AAPL",
            current_price=150.0,
            prices_7d_ago=145.0
        )
        
        # Test successful calculation logging
        stock = self.engine.calculate_stock_momentum(
            "AAPL", "Apple Inc.", 150.0, 2_500_000_000_000, historical_data
        )
        
        mock_logger.debug.assert_called()
        
        # Test market cap threshold logging
        small_stock = self.engine.calculate_stock_momentum(
            "SMALL", "Small Corp", 10.0, 5_000_000_000, historical_data
        )
        
        mock_logger.debug.assert_called_with(
            "Skipping SMALL: market cap 5000000000 below $10B threshold"
        )