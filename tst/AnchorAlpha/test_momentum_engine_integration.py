"""
Integration tests for momentum calculation engine.
"""

import pytest
from AnchorAlpha.momentum_engine import MomentumEngine, HistoricalPriceData


class TestMomentumEngineIntegration:
    """Integration tests for the complete momentum calculation workflow."""
    
    def test_complete_momentum_workflow(self):
        """Test the complete workflow from raw data to tier rankings."""
        engine = MomentumEngine()
        
        # Sample stock data representing different tiers and momentum patterns
        stock_data = [
            # 1T+ tier stocks
            ("AAPL", "Apple Inc.", 150.0, 2_500_000_000_000,
             HistoricalPriceData("AAPL", 150.0, 145.0, 140.0, 135.0, 130.0)),
            ("MSFT", "Microsoft Corp.", 300.0, 2_200_000_000_000,
             HistoricalPriceData("MSFT", 300.0, 295.0, 290.0, 285.0, 280.0)),
            
            # 500B-1T tier stocks
            ("NVDA", "NVIDIA Corp.", 800.0, 800_000_000_000,
             HistoricalPriceData("NVDA", 800.0, 760.0, 720.0, 680.0, 640.0)),
            ("TSLA", "Tesla Inc.", 200.0, 600_000_000_000,
             HistoricalPriceData("TSLA", 200.0, 190.0, 180.0, 170.0, 160.0)),
            ("META", "Meta Platforms", 300.0, 750_000_000_000,
             HistoricalPriceData("META", 300.0, 295.0, 285.0, 275.0, 265.0)),
            
            # 200B-500B tier stocks
            ("BRK.A", "Berkshire Hathaway", 500000.0, 400_000_000_000,
             HistoricalPriceData("BRK.A", 500000.0, 495000.0, 490000.0, 485000.0, 480000.0)),
            ("UNH", "UnitedHealth Group", 500.0, 450_000_000_000,
             HistoricalPriceData("UNH", 500.0, 490.0, 480.0, 470.0, 460.0)),
            ("JNJ", "Johnson & Johnson", 160.0, 420_000_000_000,
             HistoricalPriceData("JNJ", 160.0, 158.0, 156.0, 154.0, 152.0)),
            
            # 100B-200B tier stocks
            ("V", "Visa Inc.", 250.0, 180_000_000_000,
             HistoricalPriceData("V", 250.0, 245.0, 240.0, 235.0, 230.0)),
            ("NFLX", "Netflix Inc.", 400.0, 170_000_000_000,
             HistoricalPriceData("NFLX", 400.0, 390.0, 380.0, 370.0, 360.0)),
            ("CRM", "Salesforce Inc.", 200.0, 160_000_000_000,
             HistoricalPriceData("CRM", 200.0, 195.0, 190.0, 185.0, 180.0)),
            
            # Stock below market cap threshold (should be filtered out)
            ("SMALL", "Small Corp", 50.0, 5_000_000_000,
             HistoricalPriceData("SMALL", 50.0, 49.0, 48.0, 47.0, 46.0)),
            
            # Stock with missing historical data (should be filtered out)
            ("NODATA", "No Data Corp", 100.0, 200_000_000_000,
             HistoricalPriceData("NODATA", 100.0)),  # No historical prices
        ]
        
        # Step 1: Process stock batch
        processed_stocks = engine.process_stock_batch(stock_data)
        
        # Verify filtering worked correctly
        assert len(processed_stocks) == 11  # 13 input stocks - 2 filtered out
        tickers = [stock.ticker for stock in processed_stocks]
        assert "SMALL" not in tickers  # Below market cap threshold
        assert "NODATA" not in tickers  # No historical data
        
        # Step 2: Generate tier rankings
        tier_rankings = engine.generate_tier_rankings(processed_stocks, top_n=5)
        
        # Verify tier structure
        assert len(tier_rankings) == 4
        assert all(tier in tier_rankings for tier in ["1T_plus", "500B_1T", "200B_500B", "100B_200B"])
        
        # Verify each tier has rankings for all time windows
        for tier, time_windows in tier_rankings.items():
            assert len(time_windows) == 4  # 7, 30, 60, 90 day windows
            assert all(window in time_windows for window in [7, 30, 60, 90])
        
        # Step 3: Verify tier distributions
        tier_1t = tier_rankings["1T_plus"]
        tier_500b = tier_rankings["500B_1T"]
        tier_200b = tier_rankings["200B_500B"]
        tier_100b = tier_rankings["100B_200B"]
        
        # Check 1T+ tier has 2 stocks
        assert len(tier_1t[7]) == 2
        assert all(stock.ticker in ["AAPL", "MSFT"] for stock in tier_1t[7])
        
        # Check 500B-1T tier has 3 stocks
        assert len(tier_500b[7]) == 3
        assert all(stock.ticker in ["NVDA", "TSLA", "META"] for stock in tier_500b[7])
        
        # Check 200B-500B tier has 3 stocks
        assert len(tier_200b[7]) == 3
        assert all(stock.ticker in ["BRK.A", "UNH", "JNJ"] for stock in tier_200b[7])
        
        # Check 100B-200B tier has 3 stocks
        assert len(tier_100b[7]) == 3
        assert all(stock.ticker in ["V", "NFLX", "CRM"] for stock in tier_100b[7])
        
        # Step 4: Verify momentum calculations are reasonable
        for tier_stocks in tier_rankings.values():
            for time_window, stocks in tier_stocks.items():
                for stock in stocks:
                    momentum = stock.get_momentum(time_window)
                    assert momentum is not None
                    assert -1.0 <= momentum <= 10.0  # Within reasonable bounds
        
        # Step 5: Verify ranking order (highest momentum first)
        for tier_stocks in tier_rankings.values():
            for time_window, stocks in tier_stocks.items():
                if len(stocks) > 1:
                    for i in range(len(stocks) - 1):
                        current_momentum = stocks[i].get_momentum(time_window)
                        next_momentum = stocks[i + 1].get_momentum(time_window)
                        # Current should be >= next (descending order)
                        assert current_momentum >= next_momentum
        
        # Step 6: Validate data quality
        validation_stats = engine.validate_momentum_data(processed_stocks)
        
        assert validation_stats["total_stocks"] == 11
        assert validation_stats["stocks_with_7d"] == 11  # All should have 7d data
        assert validation_stats["stocks_with_30d"] == 11  # All should have 30d data
        assert validation_stats["stocks_with_60d"] == 11  # All should have 60d data
        assert validation_stats["stocks_with_90d"] == 11  # All should have 90d data
        assert validation_stats["stocks_with_all_windows"] == 11  # All complete
    
    def test_momentum_calculation_accuracy(self):
        """Test that momentum calculations are mathematically correct."""
        engine = MomentumEngine()
        
        # Test with known values for easy verification
        historical_data = HistoricalPriceData(
            ticker="TEST",
            current_price=110.0,
            prices_7d_ago=100.0,  # 10% gain over 7 days
            prices_30d_ago=90.0,  # 22.22% gain over 30 days
            prices_60d_ago=80.0,  # 37.5% gain over 60 days
            prices_90d_ago=70.0   # 57.14% gain over 90 days
        )
        
        stock = engine.calculate_stock_momentum(
            ticker="TEST",
            company_name="Test Corp",
            current_price=110.0,
            market_cap=500_000_000_000,
            historical_data=historical_data
        )
        
        assert stock is not None
        
        # Verify momentum calculations with tolerance for floating point precision
        assert abs(stock.momentum_7d - 0.10) < 0.0001  # 10%
        assert abs(stock.momentum_30d - (110.0/90.0 - 1)) < 0.0001  # ~22.22%
        assert abs(stock.momentum_60d - 0.375) < 0.0001  # 37.5%
        assert abs(stock.momentum_90d - (110.0/70.0 - 1)) < 0.0001  # ~57.14%
    
    def test_edge_case_handling(self):
        """Test handling of various edge cases."""
        engine = MomentumEngine()
        
        edge_case_data = [
            # Stock with extreme positive momentum
            ("EXTREME_UP", "Extreme Up", 1000.0, 500_000_000_000,
             HistoricalPriceData("EXTREME_UP", 1000.0, 100.0)),  # 900% gain
            
            # Stock with extreme negative momentum
            ("EXTREME_DOWN", "Extreme Down", 10.0, 400_000_000_000,
             HistoricalPriceData("EXTREME_DOWN", 10.0, 100.0)),  # -90% loss
            
            # Stock with zero momentum
            ("FLAT", "Flat Stock", 100.0, 300_000_000_000,
             HistoricalPriceData("FLAT", 100.0, 100.0, 100.0, 100.0, 100.0)),
            
            # Stock with mixed momentum patterns
            ("MIXED", "Mixed Pattern", 100.0, 200_000_000_000,
             HistoricalPriceData("MIXED", 100.0, 105.0, 95.0, 110.0, 90.0)),
        ]
        
        processed_stocks = engine.process_stock_batch(edge_case_data)
        
        # All stocks should be processed successfully
        assert len(processed_stocks) == 4
        
        # Find specific stocks
        extreme_up = next(s for s in processed_stocks if s.ticker == "EXTREME_UP")
        extreme_down = next(s for s in processed_stocks if s.ticker == "EXTREME_DOWN")
        flat = next(s for s in processed_stocks if s.ticker == "FLAT")
        mixed = next(s for s in processed_stocks if s.ticker == "MIXED")
        
        # Verify extreme momentum capping
        assert extreme_up.momentum_7d == 9.0  # (1000/100) - 1 = 9.0 (900%)
        assert extreme_down.momentum_7d == -0.9  # Capped at -90%
        
        # Verify zero momentum
        assert flat.momentum_7d == 0.0
        assert flat.momentum_30d == 0.0
        assert flat.momentum_60d == 0.0
        assert flat.momentum_90d == 0.0
        
        # Verify mixed patterns are calculated correctly
        assert mixed.momentum_7d < 0  # 100 vs 105 = negative
        assert mixed.momentum_30d > 0  # 100 vs 95 = positive
        assert mixed.momentum_60d < 0  # 100 vs 110 = negative
        assert mixed.momentum_90d > 0  # 100 vs 90 = positive