"""
Configuration management for AnchorAlpha.
"""

import os
from typing import Optional


class Config:
    """Configuration settings for AnchorAlpha application."""
    
    # API Configuration
    FMP_API_KEY: str = os.getenv("FMP_API_KEY", "")
    FMP_BASE_URL: str = "https://financialmodelingprep.com/api/v3"
    PERPLEXITY_API_KEY: str = os.getenv("PERPLEXITY_API_KEY", "")
    PERPLEXITY_BASE_URL: str = "https://api.perplexity.ai"
    
    # Market Cap Thresholds (in USD)
    MIN_MARKET_CAP: int = 10_000_000_000  # $10B
    TIER_THRESHOLDS = {
        "100B_200B": (100_000_000_000, 200_000_000_000),
        "200B_500B": (200_000_000_000, 500_000_000_000),
        "500B_1T": (500_000_000_000, 1_000_000_000_000),
        "1T_plus": (1_000_000_000_000, float('inf'))
    }
    
    # Momentum Configuration
    MOMENTUM_WINDOWS: list = [7, 30, 60, 90]  # Days
    TOP_PERFORMERS_COUNT: int = 20
    
    # AWS Configuration
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    S3_BUCKET: str = os.getenv("S3_BUCKET", "anchoralpha-data")
    S3_KEY_PREFIX: str = "momentum-data"
    
    # Rate Limiting
    FMP_REQUESTS_PER_MINUTE: int = 300  # Free tier limit
    PERPLEXITY_REQUESTS_PER_MINUTE: int = 60  # Conservative rate limit
    
    # Data Quality
    MAX_MOMENTUM_VALUE: float = 10.0  # 1000% cap
    MIN_MOMENTUM_VALUE: float = -0.9  # -90% floor
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration values."""
        if not cls.FMP_API_KEY:
            raise ValueError("FMP_API_KEY environment variable is required")
        
        return True
    
    @classmethod
    def get_fmp_url(cls, endpoint: str) -> str:
        """Construct FMP API URL with endpoint."""
        return f"{cls.FMP_BASE_URL}/{endpoint}?apikey={cls.FMP_API_KEY}"