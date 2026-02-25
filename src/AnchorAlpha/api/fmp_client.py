"""
Financial Modeling Prep (FMP) API client for stock data.
"""

import requests
import time
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import logging

from ..models import Stock
from ...cfg.config import Config

logger = logging.getLogger(__name__)


class FMPAPIError(Exception):
    """Custom exception for FMP API errors."""
    pass


class RateLimiter:
    """Simple rate limiter for API requests."""
    
    def __init__(self, requests_per_minute: int = 300):
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
                logger.info(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
        
        self.requests.append(now)


class FMPClient:
    """Client for Financial Modeling Prep API."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Config.FMP_API_KEY
        self.base_url = Config.FMP_BASE_URL
        self.rate_limiter = RateLimiter(Config.FMP_REQUESTS_PER_MINUTE)
        
        if not self.api_key:
            raise ValueError("FMP API key is required")
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated request to FMP API."""
        self.rate_limiter.wait_if_needed()
        
        url = f"{self.base_url}/{endpoint}"
        request_params = {"apikey": self.api_key}
        
        if params:
            request_params.update(params)
        
        try:
            logger.info(f"Making FMP API request to {endpoint}")
            response = requests.get(url, params=request_params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API error messages
            if isinstance(data, dict) and "Error Message" in data:
                raise FMPAPIError(f"FMP API Error: {data['Error Message']}")
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {endpoint}: {e}")
            raise FMPAPIError(f"Request failed: {e}")
        except ValueError as e:
            logger.error(f"Invalid JSON response from {endpoint}: {e}")
            raise FMPAPIError(f"Invalid JSON response: {e}")
    
    def get_stock_screener(self, market_cap_more_than: int = None) -> List[Dict[str, Any]]:
        """
        Get stocks using the stock screener endpoint.
        
        Args:
            market_cap_more_than: Minimum market cap filter
            
        Returns:
            List of stock data dictionaries
        """
        params = {}
        
        if market_cap_more_than:
            params["marketCapMoreThan"] = market_cap_more_than
        
        # Add filters for US stocks
        params.update({
            "country": "US",
            "exchange": "NASDAQ,NYSE",
            "limit": 1000  # Get more stocks to ensure we have enough large caps
        })
        
        try:
            data = self._make_request("stock-screener", params)
            logger.info(f"Retrieved {len(data)} stocks from screener")
            return data
            
        except FMPAPIError as e:
            logger.error(f"Failed to get stock screener data: {e}")
            raise
    
    def get_large_cap_stocks(self) -> List[Dict[str, Any]]:
        """Get large-cap US stocks (>$10B market cap)."""
        return self.get_stock_screener(market_cap_more_than=Config.MIN_MARKET_CAP)
    
    def get_historical_prices(self, symbol: str, days: int = 100) -> Dict[str, Any]:
        """
        Get historical price data for a stock.
        
        Args:
            symbol: Stock ticker symbol
            days: Number of days of historical data to fetch
            
        Returns:
            Historical price data
        """
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        params = {
            "from": start_date.strftime("%Y-%m-%d"),
            "to": end_date.strftime("%Y-%m-%d")
        }
        
        try:
            data = self._make_request(f"historical-price-full/{symbol}", params)
            
            if "historical" not in data:
                logger.warning(f"No historical data found for {symbol}")
                return {"historical": []}
            
            logger.info(f"Retrieved {len(data['historical'])} historical prices for {symbol}")
            return data
            
        except FMPAPIError as e:
            logger.error(f"Failed to get historical prices for {symbol}: {e}")
            raise
    
    def get_company_profile(self, symbol: str) -> Dict[str, Any]:
        """Get company profile information."""
        try:
            data = self._make_request(f"profile/{symbol}")
            
            if not data or len(data) == 0:
                logger.warning(f"No profile data found for {symbol}")
                return {}
            
            return data[0] if isinstance(data, list) else data
            
        except FMPAPIError as e:
            logger.error(f"Failed to get company profile for {symbol}: {e}")
            raise
    
    def create_stock_from_screener_data(self, stock_data: Dict[str, Any]) -> Optional[Stock]:
        """
        Create Stock object from screener API response.
        
        Args:
            stock_data: Raw stock data from FMP screener API
            
        Returns:
            Stock object or None if data is invalid
        """
        try:
            # Extract required fields with validation
            ticker = stock_data.get("symbol", "").strip()
            company_name = stock_data.get("companyName", "").strip()
            
            # Handle price - could be in different fields
            current_price = (
                stock_data.get("price") or 
                stock_data.get("lastAnnualDividend") or 
                0.0
            )
            
            # Handle market cap - ensure it's an integer
            market_cap = stock_data.get("marketCap", 0)
            if isinstance(market_cap, str):
                # Remove any formatting and convert to int
                market_cap = int(float(market_cap.replace(",", "").replace("$", "")))
            
            # Validate required fields
            if not ticker or not company_name:
                logger.warning(f"Missing required fields for stock: {stock_data}")
                return None
            
            if current_price <= 0:
                logger.warning(f"Invalid price for {ticker}: {current_price}")
                return None
            
            if market_cap < Config.MIN_MARKET_CAP:
                logger.debug(f"Market cap too small for {ticker}: {market_cap}")
                return None
            
            return Stock(
                ticker=ticker,
                company_name=company_name,
                current_price=float(current_price),
                market_cap=int(market_cap)
            )
            
        except (ValueError, TypeError) as e:
            logger.error(f"Error creating stock from data {stock_data}: {e}")
            return None
    
    def get_stocks_by_market_cap_tier(self) -> Dict[str, List[Stock]]:
        """
        Get stocks organized by market cap tiers.
        
        Returns:
            Dictionary with tier names as keys and lists of Stock objects as values
        """
        try:
            # Get all large-cap stocks
            screener_data = self.get_large_cap_stocks()
            
            # Convert to Stock objects and filter valid ones
            stocks = []
            for stock_data in screener_data:
                stock = self.create_stock_from_screener_data(stock_data)
                if stock:
                    stocks.append(stock)
            
            logger.info(f"Created {len(stocks)} valid Stock objects")
            
            # Organize by tiers
            tiers = {
                "100B_200B": [],
                "200B_500B": [],
                "500B_1T": [],
                "1T_plus": []
            }
            
            for stock in stocks:
                tier = stock.get_tier()
                if tier in tiers:
                    tiers[tier].append(stock)
            
            # Log tier distribution
            for tier, tier_stocks in tiers.items():
                logger.info(f"Tier {tier}: {len(tier_stocks)} stocks")
            
            return tiers
            
        except Exception as e:
            logger.error(f"Error organizing stocks by tier: {e}")
            raise FMPAPIError(f"Failed to get stocks by tier: {e}")