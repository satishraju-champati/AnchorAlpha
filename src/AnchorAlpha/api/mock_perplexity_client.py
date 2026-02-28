"""
Mock Perplexity client for development when API key is not available.
Generates realistic-looking AI summaries for testing and development.
"""

import random
import time
import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


class MockPerplexityClient:
    """Mock client that simulates Perplexity API responses."""
    
    # Template summaries for different momentum patterns
    SUMMARY_TEMPLATES = {
        "high_positive": [
            "{company} is experiencing strong momentum driven by {catalyst}. Recent {timeframe} performance shows investor confidence in the company's {strength}.",
            "{company} shares are surging following {catalyst}. The {momentum_desc} momentum reflects positive market sentiment around {strength}.",
            "{company} continues its upward trajectory with {catalyst} boosting investor optimism. Strong {timeframe} performance indicates {strength}."
        ],
        "moderate_positive": [
            "{company} shows steady gains supported by {catalyst}. The company's {strength} continues to drive moderate positive momentum.",
            "{company} maintains upward momentum as {catalyst} supports investor confidence. Recent performance reflects solid {strength}.",
            "{company} demonstrates consistent growth with {catalyst} contributing to positive market sentiment and strong {strength}."
        ],
        "mixed": [
            "{company} shows mixed performance as {catalyst} creates both opportunities and challenges. Investors are weighing {strength} against market uncertainties.",
            "{company} faces a complex market environment with {catalyst} influencing trading patterns. The company's {strength} remains a key focus for investors.",
            "{company} navigates market volatility with {catalyst} creating mixed investor sentiment. Strong {strength} provides some stability."
        ],
        "moderate_negative": [
            "{company} faces headwinds from {catalyst}, though the company's underlying {strength} remains intact. Recent performance reflects market concerns.",
            "{company} experiences pressure due to {catalyst}, leading to cautious investor sentiment. However, long-term {strength} continues to support the stock.",
            "{company} encounters challenges from {catalyst}, resulting in recent underperformance. Investors are monitoring the company's {strength}."
        ],
        "high_negative": [
            "{company} is under significant pressure following {catalyst}. The sharp decline reflects serious investor concerns about {strength}.",
            "{company} faces major challenges as {catalyst} severely impacts investor confidence. Recent performance highlights concerns about {strength}.",
            "{company} struggles with {catalyst}, leading to substantial selling pressure. Market sentiment around {strength} has turned negative."
        ]
    }
    
    # Realistic catalysts and strengths for different scenarios
    CATALYSTS = [
        "strong quarterly earnings results",
        "positive analyst upgrades",
        "new product launches and innovations",
        "strategic partnership announcements",
        "market expansion initiatives",
        "regulatory approval news",
        "management guidance updates",
        "sector rotation trends",
        "macroeconomic developments",
        "competitive positioning improvements",
        "cost reduction initiatives",
        "dividend announcements",
        "share buyback programs",
        "merger and acquisition activity",
        "supply chain optimizations"
    ]
    
    STRENGTHS = [
        "core business fundamentals",
        "market leadership position",
        "innovative product portfolio",
        "operational efficiency",
        "financial stability",
        "growth prospects",
        "competitive advantages",
        "brand strength",
        "technological capabilities",
        "customer loyalty",
        "revenue diversification",
        "margin expansion potential",
        "cash generation ability",
        "strategic positioning",
        "management execution"
    ]
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize mock client."""
        self.api_key = api_key or "mock_key"
        logger.info("Initialized MockPerplexityClient for development")
    
    def _classify_momentum(self, momentum_data: Dict[str, float]) -> str:
        """Classify overall momentum pattern."""
        # Calculate average momentum (excluding None values)
        valid_momentum = [m for m in momentum_data.values() if m is not None]
        
        if not valid_momentum:
            return "mixed"
        
        avg_momentum = sum(valid_momentum) / len(valid_momentum)
        
        if avg_momentum > 0.10:  # >10%
            return "high_positive"
        elif avg_momentum > 0.03:  # >3%
            return "moderate_positive"
        elif avg_momentum > -0.03:  # -3% to 3%
            return "mixed"
        elif avg_momentum > -0.10:  # -10% to -3%
            return "moderate_negative"
        else:  # <-10%
            return "high_negative"
    
    def _get_timeframe_description(self, momentum_data: Dict[str, float]) -> str:
        """Get description of timeframe performance."""
        timeframes = []
        for period, momentum in momentum_data.items():
            if momentum is not None and abs(momentum) > 0.02:  # >2% movement
                timeframes.append(period.replace("-", "-day "))
        
        if not timeframes:
            return "recent"
        elif len(timeframes) == 1:
            return timeframes[0]
        else:
            return f"{timeframes[0]} and {timeframes[-1]}"
    
    def _get_momentum_description(self, momentum_data: Dict[str, float]) -> str:
        """Get description of momentum strength."""
        valid_momentum = [abs(m) for m in momentum_data.values() if m is not None]
        
        if not valid_momentum:
            return "steady"
        
        max_momentum = max(valid_momentum)
        
        if max_momentum > 0.15:  # >15%
            return "exceptional"
        elif max_momentum > 0.08:  # >8%
            return "strong"
        elif max_momentum > 0.03:  # >3%
            return "moderate"
        else:
            return "modest"
    
    def generate_stock_summary(self, ticker: str, company_name: str, momentum_data: Dict[str, float]) -> str:
        """Generate mock AI summary for stock movement."""
        try:
            # Add small delay to simulate API call
            time.sleep(0.1)
            
            # Classify momentum pattern
            momentum_pattern = self._classify_momentum(momentum_data)
            
            # Select random template for this pattern
            templates = self.SUMMARY_TEMPLATES[momentum_pattern]
            template = random.choice(templates)
            
            # Fill in template variables
            summary = template.format(
                company=company_name,
                catalyst=random.choice(self.CATALYSTS),
                strength=random.choice(self.STRENGTHS),
                timeframe=self._get_timeframe_description(momentum_data),
                momentum_desc=self._get_momentum_description(momentum_data)
            )
            
            logger.info(f"Generated mock summary for {ticker}: {len(summary)} characters")
            return summary
            
        except Exception as e:
            logger.error(f"Error generating mock summary for {ticker}: {e}")
            return f"Market analysis for {company_name} is currently unavailable."
    
    def generate_batch_summaries(self, stocks_data: List[Dict[str, Any]]) -> Dict[str, str]:
        """Generate mock summaries for multiple stocks."""
        summaries = {}
        
        for stock_info in stocks_data:
            ticker = stock_info.get("ticker")
            company_name = stock_info.get("company_name")
            momentum_data = stock_info.get("momentum_data", {})
            
            if not ticker or not company_name:
                logger.warning(f"Missing required data for stock: {stock_info}")
                continue
            
            try:
                summary = self.generate_stock_summary(ticker, company_name, momentum_data)
                summaries[ticker] = summary
                
                # Small delay between requests to simulate rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error generating mock summary for {ticker}: {e}")
                summaries[ticker] = f"Summary for {company_name} is currently unavailable."
        
        logger.info(f"Generated {len(summaries)} mock stock summaries")
        return summaries
    
    def test_api_connection(self) -> bool:
        """Mock API connection test - always returns True."""
        time.sleep(0.1)  # Simulate network delay
        logger.info("Mock Perplexity API connection test successful")
        return True