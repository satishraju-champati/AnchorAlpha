"""
Unit tests for MockDataProvider.
"""

import pytest
import logging
from AnchorAlpha.api.mock_data_provider import MockDataProvider

logger = logging.getLogger(__name__)


class TestMockDataProvider:
    """Test cases for MockDataProvider."""
    
    def test_large_cap_stock_generation(self):
        """Test large-cap stock data generation."""
        provider = MockDataProvider()
        stocks_data = provider.get_large_cap_stocks()
        
        assert len(stocks_data) > 0
        assert len(stocks_data) <= 100  # Reasonable upper bound
        
        # Test sample stock structure
        if stocks_data:
            sample = stocks_data[0]
            required_fields = ["symbol", "companyName", "price", "marketCap"]
            for field in required_fields:
                assert field in sample
                assert sample[field] is not None
            
            # Validate data types and ranges
            assert isinstance(sample["price"], (int, float))
            assert sample["price"] > 0
            assert isinstance(sample["marketCap"], int)
            assert sample["marketCap"] >= 10_000_000_000  # $10B minimum
    
    def test_tier_organization(self):
        """Test stock organization by market cap tiers."""
        provider = MockDataProvider()
        tiers = provider.get_stocks_by_market_cap_tier()
        
        # Verify all tiers exist
        expected_tiers = ["100B_200B", "200B_500B", "500B_1T", "1T_plus"]
        for tier in expected_tiers:
            assert tier in tiers
            assert isinstance(tiers[tier], list)
        
        # Verify tier classification is correct
        for tier_name, tier_stocks in tiers.items():
            for stock in tier_stocks:
                calculated_tier = stock.get_tier()
                assert calculated_tier == tier_name
    
    def test_historical_price_generation(self):
        """Test historical price data generation."""
        provider = MockDataProvider()
        historical_data = provider.get_historical_prices("AAPL", days=30)
        
        assert "historical" in historical_data
        assert "symbol" in historical_data
        assert historical_data["symbol"] == "AAPL"
        
        prices = historical_data["historical"]
        assert len(prices) == 30
        
        # Test price data structure
        if prices:
            price_data = prices[0]
            required_fields = ["date", "open", "high", "low", "close", "volume"]
            for field in required_fields:
                assert field in price_data
                assert price_data[field] is not None
            
            # Validate price relationships
            assert price_data["low"] <= price_data["close"] <= price_data["high"]
            assert price_data["volume"] > 0
    
    def test_stock_creation_from_data(self):
        """Test Stock object creation from mock data."""
        provider = MockDataProvider()
        stocks_data = provider.get_large_cap_stocks()
        
        if stocks_data:
            sample_data = stocks_data[0]
            stock = provider.create_stock_from_data(sample_data)
            
            assert stock is not None
            assert stock.ticker == sample_data["symbol"]
            assert stock.company_name == sample_data["companyName"]
            assert stock.current_price == sample_data["price"]
            assert stock.market_cap == sample_data["marketCap"]
    
    def test_invalid_stock_data_handling(self):
        """Test handling of invalid stock data."""
        provider = MockDataProvider()
        
        # Test with invalid data
        invalid_data = {
            "symbol": "",  # Empty symbol
            "companyName": "Test Corp",
            "price": 100.0,
            "marketCap": 50_000_000_000
        }
        
        stock = provider.create_stock_from_data(invalid_data)
        assert stock is None
        
        # Test with small market cap
        small_cap_data = {
            "symbol": "SMALL",
            "companyName": "Small Corp",
            "price": 10.0,
            "marketCap": 5_000_000_000  # Below $10B threshold
        }
        
        stock = provider.create_stock_from_data(small_cap_data)
        assert stock is None