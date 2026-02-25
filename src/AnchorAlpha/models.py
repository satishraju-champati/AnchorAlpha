"""
Core data models for AnchorAlpha momentum screener.
"""

from dataclasses import dataclass
from typing import Optional, Dict
from decimal import Decimal


@dataclass
class Stock:
    """Represents a stock with momentum data."""
    
    ticker: str
    company_name: str
    current_price: float
    market_cap: int
    momentum_7d: Optional[float] = None
    momentum_30d: Optional[float] = None
    momentum_60d: Optional[float] = None
    momentum_90d: Optional[float] = None
    ai_summary: Optional[str] = None
    
    def __post_init__(self):
        """Validate stock data after initialization."""
        if self.market_cap < 10_000_000_000:  # $10B minimum
            raise ValueError(f"Market cap {self.market_cap} below $10B threshold")
        
        if self.current_price <= 0:
            raise ValueError(f"Invalid current price: {self.current_price}")
    
    def get_tier(self) -> str:
        """Categorize stock by market cap tier."""
        if self.market_cap >= 1_000_000_000_000:  # $1T+
            return "1T_plus"
        elif self.market_cap >= 500_000_000_000:  # $500B-$1T
            return "500B_1T"
        elif self.market_cap >= 200_000_000_000:  # $200B-$500B
            return "200B_500B"
        else:  # $100B-$200B
            return "100B_200B"
    
    def get_momentum(self, days: int) -> Optional[float]:
        """Get momentum for specified time window."""
        momentum_map = {
            7: self.momentum_7d,
            30: self.momentum_30d,
            60: self.momentum_60d,
            90: self.momentum_90d
        }
        return momentum_map.get(days)


@dataclass
class MomentumCalculation:
    """Handles momentum calculations for a stock."""
    
    ticker: str
    current_price: float
    historical_prices: Dict[int, float]  # {days_ago: price}
    
    def __post_init__(self):
        """Validate calculation inputs."""
        if self.current_price <= 0:
            raise ValueError(f"Invalid current price: {self.current_price}")
        
        for days, price in self.historical_prices.items():
            if price <= 0:
                raise ValueError(f"Invalid historical price for {days} days ago: {price}")
    
    def calculate_momentum(self, days: int) -> Optional[float]:
        """
        Calculate momentum: (current_price / price_n_days_ago) - 1
        
        Args:
            days: Number of days back to calculate momentum
            
        Returns:
            Momentum as decimal (e.g., 0.05 for 5% gain) or None if data unavailable
        """
        if days not in self.historical_prices:
            return None
        
        historical_price = self.historical_prices[days]
        momentum = (self.current_price / historical_price) - 1
        
        # Cap extreme values for data quality
        if momentum > 10.0:  # 1000% cap
            return 10.0
        elif momentum < -0.9:  # -90% floor
            return -0.9
        
        return momentum
    
    def calculate_all_momentum(self) -> Dict[int, Optional[float]]:
        """Calculate momentum for all standard time windows."""
        return {
            7: self.calculate_momentum(7),
            30: self.calculate_momentum(30),
            60: self.calculate_momentum(60),
            90: self.calculate_momentum(90)
        }