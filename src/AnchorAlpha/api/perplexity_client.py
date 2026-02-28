"""
Perplexity Sonar API client for generating AI summaries of stock movements.
"""

import requests
import time
from typing import List, Dict, Optional, Any
import logging

# Import config with fallback
try:
    from cfg.config import Config
except ImportError:
    # Fallback config for testing
    class Config:
        PERPLEXITY_API_KEY = ""
        PERPLEXITY_REQUESTS_PER_MINUTE = 60

logger = logging.getLogger(__name__)


class PerplexityAPIError(Exception):
    """Custom exception for Perplexity API errors."""
    pass


class PerplexityRateLimiter:
    """Rate limiter for Perplexity API requests."""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = []
    
    def wait_if_needed(self):
        """Wait if we're approaching rate limit."""
        now = time.time()
        # Remove requests older than 1 minute
        self.requests = [req_time for req_time in self.requests if now - req_time < 60]
        
        if len(self.requests) >= self.requests_per_minute:
            sleep_time = 60 - (now - self.requests[0])
            if sleep_time > 0:
                logger.info(f"Perplexity rate limit reached, sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
        
        self.requests.append(now)


class PerplexityClient:
    """Client for Perplexity Sonar API."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Config.PERPLEXITY_API_KEY
        self.base_url = "https://api.perplexity.ai"
        self.rate_limiter = PerplexityRateLimiter(Config.PERPLEXITY_REQUESTS_PER_MINUTE)
        
        if not self.api_key:
            raise ValueError("Perplexity API key is required")
    
    def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make authenticated request to Perplexity API."""
        self.rate_limiter.wait_if_needed()
        
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            logger.info(f"Making Perplexity API request to {endpoint}")
            response = requests.post(url, json=data, headers=headers, timeout=30)
            response.raise_for_status()
            
            response_data = response.json()
            
            # Check for API error messages
            if "error" in response_data:
                raise PerplexityAPIError(f"Perplexity API Error: {response_data['error']}")
            
            return response_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {endpoint}: {e}")
            raise PerplexityAPIError(f"Request failed: {e}")
        except ValueError as e:
            logger.error(f"Invalid JSON response from {endpoint}: {e}")
            raise PerplexityAPIError(f"Invalid JSON response: {e}")
    
    def generate_stock_summary(self, ticker: str, company_name: str, momentum_data: Dict[str, float]) -> str:
        """
        Generate AI summary for why a stock is moving.
        
        Args:
            ticker: Stock ticker symbol
            company_name: Company name
            momentum_data: Dictionary with momentum percentages for different time windows
            
        Returns:
            AI-generated summary explaining stock movement
        """
        try:
            # Create a focused prompt for stock analysis
            momentum_text = []
            for period, momentum in momentum_data.items():
                if momentum is not None:
                    momentum_pct = momentum * 100
                    momentum_text.append(f"{period}: {momentum_pct:+.1f}%")
            
            momentum_summary = ", ".join(momentum_text)
            
            prompt = f"""Analyze the recent stock performance of {company_name} ({ticker}) and explain why it's moving.

Recent momentum data: {momentum_summary}

Please provide a concise 2-3 sentence summary explaining:
1. What recent news, events, or market factors are driving this stock movement
2. Key business developments or market sentiment affecting the company

Focus on factual, recent developments. Keep the response under 150 words."""

            data = {
                "model": "sonar-pro",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a financial analyst providing concise explanations for stock price movements based on recent news and market developments."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 200,
                "temperature": 0.2,
                "top_p": 0.9
            }
            
            response = self._make_request("chat/completions", data)
            
            if "choices" in response and len(response["choices"]) > 0:
                summary = response["choices"][0]["message"]["content"].strip()
                logger.info(f"Generated summary for {ticker}: {len(summary)} characters")
                return summary
            else:
                logger.warning(f"No summary generated for {ticker}")
                return f"Unable to generate summary for {company_name} at this time."
                
        except PerplexityAPIError as e:
            logger.error(f"Failed to generate summary for {ticker}: {e}")
            return f"Market analysis for {company_name} is currently unavailable."
        except Exception as e:
            logger.error(f"Unexpected error generating summary for {ticker}: {e}")
            return f"Summary for {company_name} could not be generated."
    
    def generate_batch_summaries(self, stocks_data: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Generate summaries for multiple stocks.
        
        Args:
            stocks_data: List of dictionaries containing stock info and momentum data
            
        Returns:
            Dictionary mapping ticker symbols to AI summaries
        """
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
                
                # Small delay between requests to be respectful
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error generating summary for {ticker}: {e}")
                summaries[ticker] = f"Summary for {company_name} is currently unavailable."
        
        logger.info(f"Generated {len(summaries)} stock summaries")
        return summaries
    
    def test_api_connection(self) -> bool:
        """
        Test if the Perplexity API is accessible with current credentials.
        
        Returns:
            True if API is accessible, False otherwise
        """
        try:
            test_data = {
                "model": "sonar-pro",
                "messages": [
                    {
                        "role": "user",
                        "content": "Hello, this is a test message. Please respond with 'API connection successful.'"
                    }
                ],
                "max_tokens": 20,
                "temperature": 0.1
            }
            
            response = self._make_request("chat/completions", test_data)
            
            if "choices" in response and len(response["choices"]) > 0:
                logger.info("Perplexity API connection test successful")
                return True
            else:
                logger.warning("Perplexity API test returned unexpected response")
                return False
                
        except Exception as e:
            logger.error(f"Perplexity API connection test failed: {e}")
            return False