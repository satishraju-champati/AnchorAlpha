"""
Unit tests for AnchorAlpha data models.
"""

import pytest
from AnchorAlpha.models import Stock, MomentumCalculation


class TestStock:
    """Test cases for Stock model."""
    
    def test_valid_stock_creation(self):
        """Test creating a valid stock instance."""
        stock = Stock(
            ticker="AAPL",
            company_name="Apple Inc.",
            current_price=150.25,
            market_cap=2_400_000_000_000,  # $2.4T
            momentum_7d=0.05,
            momentum_30d=0.12
        )
        
        assert stock.ticker == "AAPL"
        assert stock.current_price == 150.25
        assert stock.momentum_7d == 0.05
    
    def test_market_cap_validation(self):
        """Test market cap validation below $10B threshold."""
        with pytest.raises(ValueError, match="Market cap .* below \\$10B threshold"):
            Stock(
                ticker="SMALL",
                company_name="Small Corp",
                current_price=10.0,
                market_cap=5_000_000_000  # $5B - below threshold
            )
    
    def test_invalid_price_validation(self):
        """Test validation of invalid stock price."""
        with pytest.raises(ValueError, match="Invalid current price"):
            Stock(
                ticker="INVALID",
                company_name="Invalid Corp",
                current_price=-10.0,  # Negative price
                market_cap=50_000_000_000
            )
    
    def test_tier_classification(self):
        """Test market cap tier classification."""
        # Test $1T+ tier
        mega_stock = Stock("MEGA", "Mega Corp", 100.0, 1_500_000_000_000)
        assert mega_stock.get_tier() == "1T_plus"
        
        # Test $500B-$1T tier
        large_stock = Stock("LARGE", "Large Corp", 100.0, 750_000_000_000)
        assert large_stock.get_tier() == "500B_1T"
        
        # Test $200B-$500B tier
        mid_stock = Stock("MID", "Mid Corp", 100.0, 350_000_000_000)
        assert mid_stock.get_tier() == "200B_500B"
        
        # Test $100B-$200B tier
        small_stock = Stock("SMALL", "Small Corp", 100.0, 150_000_000_000)
        assert small_stock.get_tier() == "100B_200B"
    
    def test_get_momentum(self):
        """Test momentum retrieval by time window."""
        stock = Stock(
            ticker="TEST",
            company_name="Test Corp",
            current_price=100.0,
            market_cap=200_000_000_000,
            momentum_7d=0.05,
            momentum_30d=0.12,
            momentum_60d=0.08,
            momentum_90d=0.15
        )
        
        assert stock.get_momentum(7) == 0.05
        assert stock.get_momentum(30) == 0.12
        assert stock.get_momentum(45) is None  # Not a standard window


class TestMomentumCalculation:
    """Test cases for MomentumCalculation model."""
    
    def test_valid_momentum_calculation(self):
        """Test valid momentum calculation."""
        calc = MomentumCalculation(
            ticker="AAPL",
            current_price=150.0,
            historical_prices={
                7: 140.0,
                30: 130.0,
                60: 145.0,
                90: 120.0
            }
        )
        
        # Test 7-day momentum: (150/140) - 1 = 0.0714...
        momentum_7d = calc.calculate_momentum(7)
        assert abs(momentum_7d - 0.07142857142857142) < 0.0001
        
        # Test 30-day momentum: (150/130) - 1 = 0.1538...
        momentum_30d = calc.calculate_momentum(30)
        assert abs(momentum_30d - 0.15384615384615385) < 0.0001
    
    def test_missing_historical_data(self):
        """Test momentum calculation with missing historical data."""
        calc = MomentumCalculation(
            ticker="TEST",
            current_price=100.0,
            historical_prices={7: 95.0}  # Only 7-day data
        )
        
        assert calc.calculate_momentum(7) is not None
        assert calc.calculate_momentum(30) is None  # Missing data
    
    def test_invalid_current_price(self):
        """Test validation of invalid current price."""
        with pytest.raises(ValueError, match="Invalid current price"):
            MomentumCalculation(
                ticker="INVALID",
                current_price=0.0,  # Invalid price
                historical_prices={7: 100.0}
            )
    
    def test_invalid_historical_price(self):
        """Test validation of invalid historical price."""
        with pytest.raises(ValueError, match="Invalid historical price"):
            MomentumCalculation(
                ticker="INVALID",
                current_price=100.0,
                historical_prices={7: -50.0}  # Invalid historical price
            )
    
    def test_extreme_momentum_capping(self):
        """Test capping of extreme momentum values."""
        calc = MomentumCalculation(
            ticker="EXTREME",
            current_price=1000.0,
            historical_prices={
                7: 1.0,  # Would be 99900% gain
                30: 2000.0  # Would be -50% loss
            }
        )
        
        # Should cap at 1000% (10.0)
        momentum_extreme_gain = calc.calculate_momentum(7)
        assert momentum_extreme_gain == 10.0
        
        # Should cap at -90% (-0.9)
        calc_extreme_loss = MomentumCalculation(
            ticker="LOSS",
            current_price=1.0,
            historical_prices={7: 100.0}  # Would be -99% loss
        )
        momentum_extreme_loss = calc_extreme_loss.calculate_momentum(7)
        assert momentum_extreme_loss == -0.9
    
    def test_calculate_all_momentum(self):
        """Test calculating momentum for all time windows."""
        calc = MomentumCalculation(
            ticker="ALL",
            current_price=110.0,
            historical_prices={
                7: 100.0,
                30: 105.0,
                60: 108.0
                # Missing 90-day data
            }
        )
        
        all_momentum = calc.calculate_all_momentum()
        
        assert len(all_momentum) == 4
        assert all_momentum[7] == 0.1  # (110/100) - 1
        assert abs(all_momentum[30] - 0.047619047619047616) < 0.0001  # (110/105) - 1
        assert abs(all_momentum[60] - 0.018518518518518517) < 0.0001  # (110/108) - 1
        assert all_momentum[90] is None  # Missing data