"""
Unit tests for FMP API client.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from AnchorAlpha.api.fmp_client import FMPClient, FMPAPIError, RateLimiter
from AnchorAlpha.models import Stock


class TestRateLimiter:
    """Test cases for RateLimiter."""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(requests_per_minute=60)
        assert limiter.requests_per_minute == 60
        assert limiter.requests == []
    
    @patch('time.time')
    @patch('time.sleep')
    def test_rate_limiter_no_wait_needed(self, mock_sleep, mock_time):
        """Test rate limiter when no wait is needed."""
        mock_time.return_value = 100.0
        
        limiter = RateLimiter(requests_per_minute=60)
        limiter.wait_if_needed()
        
        mock_sleep.assert_not_called()
        assert len(limiter.requests) == 1


class TestFMPClient:
    """Test cases for FMPClient."""
    
    def test_client_initialization_with_api_key(self):
        """Test client initialization with API key."""
        client = FMPClient(api_key="test_key")
        assert client.api_key == "test_key"
        assert client.base_url == "https://financialmodelingprep.com/api/v3"
    
    def test_client_initialization_without_api_key(self):
        """Test client initialization fails without API key."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="FMP API key is required"):
                FMPClient()
    
    @patch('requests.get')
    def test_make_request_success(self, mock_get):
        """Test successful API request."""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        client = FMPClient(api_key="test_key")
        result = client._make_request("test-endpoint")
        
        assert result == {"data": "test"}
        mock_get.assert_called_once()
    
    @patch('requests.get')
    def test_make_request_api_error(self, mock_get):
        """Test API request with error message."""
        # Mock API error response
        mock_response = Mock()
        mock_response.json.return_value = {"Error Message": "Invalid API key"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        client = FMPClient(api_key="test_key")
        
        with pytest.raises(FMPAPIError, match="FMP API Error: Invalid API key"):
            client._make_request("test-endpoint")
    
    @patch('requests.get')
    def test_make_request_network_error(self, mock_get):
        """Test API request with network error."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")
        
        client = FMPClient(api_key="test_key")
        
        with pytest.raises(FMPAPIError, match="Request failed"):
            client._make_request("test-endpoint")
    
    @patch.object(FMPClient, '_make_request')
    def test_get_stock_screener(self, mock_request):
        """Test stock screener API call."""
        mock_request.return_value = [
            {"symbol": "AAPL", "companyName": "Apple Inc.", "marketCap": 2000000000000}
        ]
        
        client = FMPClient(api_key="test_key")
        result = client.get_stock_screener(market_cap_more_than=1000000000000)
        
        assert len(result) == 1
        assert result[0]["symbol"] == "AAPL"
        
        # Verify the request was made with correct parameters
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[0][0] == "stock-screener"
        assert call_args[1]["params"]["marketCapMoreThan"] == 1000000000000
    
    @patch.object(FMPClient, '_make_request')
    def test_get_historical_prices(self, mock_request):
        """Test historical prices API call."""
        mock_request.return_value = {
            "historical": [
                {"date": "2024-01-01", "close": 150.0},
                {"date": "2024-01-02", "close": 152.0}
            ]
        }
        
        client = FMPClient(api_key="test_key")
        result = client.get_historical_prices("AAPL", days=30)
        
        assert "historical" in result
        assert len(result["historical"]) == 2
        
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert "historical-price-full/AAPL" in call_args[0][0]
    
    def test_create_stock_from_screener_data_valid(self):
        """Test creating Stock object from valid screener data."""
        client = FMPClient(api_key="test_key")
        
        stock_data = {
            "symbol": "AAPL",
            "companyName": "Apple Inc.",
            "price": 150.25,
            "marketCap": 2400000000000
        }
        
        stock = client.create_stock_from_screener_data(stock_data)
        
        assert stock is not None
        assert stock.ticker == "AAPL"
        assert stock.company_name == "Apple Inc."
        assert stock.current_price == 150.25
        assert stock.market_cap == 2400000000000
    
    def test_create_stock_from_screener_data_invalid_price(self):
        """Test creating Stock object with invalid price."""
        client = FMPClient(api_key="test_key")
        
        stock_data = {
            "symbol": "INVALID",
            "companyName": "Invalid Corp",
            "price": 0.0,  # Invalid price
            "marketCap": 50000000000
        }
        
        stock = client.create_stock_from_screener_data(stock_data)
        assert stock is None
    
    def test_create_stock_from_screener_data_small_market_cap(self):
        """Test creating Stock object with market cap below threshold."""
        client = FMPClient(api_key="test_key")
        
        stock_data = {
            "symbol": "SMALL",
            "companyName": "Small Corp",
            "price": 10.0,
            "marketCap": 5000000000  # Below $10B threshold
        }
        
        stock = client.create_stock_from_screener_data(stock_data)
        assert stock is None
    
    def test_create_stock_from_screener_data_missing_fields(self):
        """Test creating Stock object with missing required fields."""
        client = FMPClient(api_key="test_key")
        
        stock_data = {
            "symbol": "",  # Missing symbol
            "price": 100.0,
            "marketCap": 50000000000
        }
        
        stock = client.create_stock_from_screener_data(stock_data)
        assert stock is None
    
    @patch.object(FMPClient, 'get_large_cap_stocks')
    def test_get_stocks_by_market_cap_tier(self, mock_get_stocks):
        """Test organizing stocks by market cap tiers."""
        # Mock screener data
        mock_get_stocks.return_value = [
            {"symbol": "AAPL", "companyName": "Apple Inc.", "price": 150.0, "marketCap": 2400000000000},  # 1T+
            {"symbol": "MSFT", "companyName": "Microsoft", "price": 300.0, "marketCap": 800000000000},   # 500B-1T
            {"symbol": "GOOGL", "companyName": "Alphabet", "price": 120.0, "marketCap": 300000000000},   # 200B-500B
            {"symbol": "NVDA", "companyName": "NVIDIA", "price": 400.0, "marketCap": 150000000000},      # 100B-200B
        ]
        
        client = FMPClient(api_key="test_key")
        tiers = client.get_stocks_by_market_cap_tier()
        
        assert len(tiers) == 4
        assert len(tiers["1T_plus"]) == 1
        assert len(tiers["500B_1T"]) == 1
        assert len(tiers["200B_500B"]) == 1
        assert len(tiers["100B_200B"]) == 1
        
        # Verify correct tier assignment
        assert tiers["1T_plus"][0].ticker == "AAPL"
        assert tiers["500B_1T"][0].ticker == "MSFT"
        assert tiers["200B_500B"][0].ticker == "GOOGL"
        assert tiers["100B_200B"][0].ticker == "NVDA"