"""
Unit tests for Perplexity API client.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from AnchorAlpha.api.perplexity_client import PerplexityClient, PerplexityAPIError, PerplexityRateLimiter


class TestPerplexityRateLimiter:
    """Test cases for PerplexityRateLimiter."""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        limiter = PerplexityRateLimiter(requests_per_minute=60)
        assert limiter.requests_per_minute == 60
        assert limiter.requests == []
    
    @patch('time.time')
    @patch('time.sleep')
    def test_rate_limiter_no_wait_needed(self, mock_sleep, mock_time):
        """Test rate limiter when no wait is needed."""
        mock_time.return_value = 100.0
        
        limiter = PerplexityRateLimiter(requests_per_minute=60)
        limiter.wait_if_needed()
        
        mock_sleep.assert_not_called()
        assert len(limiter.requests) == 1


class TestPerplexityClient:
    """Test cases for PerplexityClient."""
    
    def test_client_initialization_with_api_key(self):
        """Test client initialization with API key."""
        client = PerplexityClient(api_key="test_key")
        assert client.api_key == "test_key"
        assert client.base_url == "https://api.perplexity.ai"
    
    def test_client_initialization_without_api_key(self):
        """Test client initialization fails without API key."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="Perplexity API key is required"):
                PerplexityClient()
    
    @patch('requests.post')
    def test_make_request_success(self, mock_post):
        """Test successful API request."""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "test response"}}]}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        client = PerplexityClient(api_key="test_key")
        result = client._make_request("chat/completions", {"test": "data"})
        
        assert "choices" in result
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_make_request_api_error(self, mock_post):
        """Test API request with error message."""
        # Mock API error response
        mock_response = Mock()
        mock_response.json.return_value = {"error": "Invalid API key"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        client = PerplexityClient(api_key="test_key")
        
        with pytest.raises(PerplexityAPIError, match="Perplexity API Error: Invalid API key"):
            client._make_request("chat/completions", {"test": "data"})
    
    @patch('requests.post')
    def test_make_request_network_error(self, mock_post):
        """Test API request with network error."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Network error")
        
        client = PerplexityClient(api_key="test_key")
        
        with pytest.raises(PerplexityAPIError, match="Request failed"):
            client._make_request("chat/completions", {"test": "data"})
    
    @patch.object(PerplexityClient, '_make_request')
    def test_generate_stock_summary_success(self, mock_request):
        """Test successful stock summary generation."""
        mock_request.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "Apple Inc. is experiencing strong momentum due to positive earnings results and new product launches. The company's iPhone sales exceeded expectations, driving investor confidence."
                    }
                }
            ]
        }
        
        client = PerplexityClient(api_key="test_key")
        momentum_data = {
            "7-day": 0.05,
            "30-day": 0.12,
            "60-day": 0.08
        }
        
        summary = client.generate_stock_summary("AAPL", "Apple Inc.", momentum_data)
        
        assert "Apple Inc." in summary
        assert "momentum" in summary.lower() or "earnings" in summary.lower()
        mock_request.assert_called_once()
    
    @patch.object(PerplexityClient, '_make_request')
    def test_generate_stock_summary_api_error(self, mock_request):
        """Test stock summary generation with API error."""
        mock_request.side_effect = PerplexityAPIError("API quota exceeded")
        
        client = PerplexityClient(api_key="test_key")
        momentum_data = {"7-day": 0.05}
        
        summary = client.generate_stock_summary("AAPL", "Apple Inc.", momentum_data)
        
        assert "Apple Inc." in summary
        assert "unavailable" in summary.lower()
    
    @patch.object(PerplexityClient, '_make_request')
    def test_generate_stock_summary_no_choices(self, mock_request):
        """Test stock summary generation with empty response."""
        mock_request.return_value = {"choices": []}
        
        client = PerplexityClient(api_key="test_key")
        momentum_data = {"7-day": 0.05}
        
        summary = client.generate_stock_summary("AAPL", "Apple Inc.", momentum_data)
        
        assert "Apple Inc." in summary
        assert "Unable to generate" in summary
    
    @patch.object(PerplexityClient, 'generate_stock_summary')
    @patch('time.sleep')
    def test_generate_batch_summaries(self, mock_sleep, mock_generate):
        """Test batch summary generation."""
        mock_generate.side_effect = [
            "Apple is performing well due to strong earnings.",
            "Microsoft shows growth in cloud services.",
            "Google faces regulatory challenges."
        ]
        
        client = PerplexityClient(api_key="test_key")
        
        stocks_data = [
            {
                "ticker": "AAPL",
                "company_name": "Apple Inc.",
                "momentum_data": {"7-day": 0.05}
            },
            {
                "ticker": "MSFT",
                "company_name": "Microsoft Corporation",
                "momentum_data": {"7-day": 0.03}
            },
            {
                "ticker": "GOOGL",
                "company_name": "Alphabet Inc.",
                "momentum_data": {"7-day": -0.02}
            }
        ]
        
        summaries = client.generate_batch_summaries(stocks_data)
        
        assert len(summaries) == 3
        assert "AAPL" in summaries
        assert "MSFT" in summaries
        assert "GOOGL" in summaries
        assert "Apple" in summaries["AAPL"]
        assert "Microsoft" in summaries["MSFT"]
        assert "Google" in summaries["GOOGL"]
        
        # Verify sleep was called between requests
        assert mock_sleep.call_count == 3
    
    def test_generate_batch_summaries_missing_data(self):
        """Test batch summary generation with missing data."""
        client = PerplexityClient(api_key="test_key")
        
        stocks_data = [
            {
                "ticker": "AAPL",
                # Missing company_name
                "momentum_data": {"7-day": 0.05}
            },
            {
                # Missing ticker
                "company_name": "Microsoft Corporation",
                "momentum_data": {"7-day": 0.03}
            }
        ]
        
        summaries = client.generate_batch_summaries(stocks_data)
        
        # Should return empty dict due to missing required fields
        assert len(summaries) == 0
    
    @patch.object(PerplexityClient, '_make_request')
    def test_test_api_connection_success(self, mock_request):
        """Test successful API connection test."""
        mock_request.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "API connection successful."
                    }
                }
            ]
        }
        
        client = PerplexityClient(api_key="test_key")
        result = client.test_api_connection()
        
        assert result is True
        mock_request.assert_called_once()
    
    @patch.object(PerplexityClient, '_make_request')
    def test_test_api_connection_failure(self, mock_request):
        """Test failed API connection test."""
        mock_request.side_effect = PerplexityAPIError("Invalid API key")
        
        client = PerplexityClient(api_key="test_key")
        result = client.test_api_connection()
        
        assert result is False
    
    @patch.object(PerplexityClient, '_make_request')
    def test_test_api_connection_empty_response(self, mock_request):
        """Test API connection test with empty response."""
        mock_request.return_value = {"choices": []}
        
        client = PerplexityClient(api_key="test_key")
        result = client.test_api_connection()
        
        assert result is False
    
    def test_momentum_data_formatting(self):
        """Test that momentum data is properly formatted in prompts."""
        client = PerplexityClient(api_key="test_key")
        
        momentum_data = {
            "7-day": 0.0523,
            "30-day": -0.0234,
            "60-day": 0.1567,
            "90-day": None  # Should be skipped
        }
        
        with patch.object(client, '_make_request') as mock_request:
            mock_request.return_value = {
                "choices": [{"message": {"content": "Test summary"}}]
            }
            
            client.generate_stock_summary("TEST", "Test Corp", momentum_data)
            
            # Check that the prompt was formatted correctly
            call_args = mock_request.call_args[0][1]
            prompt_content = call_args["messages"][1]["content"]
            
            assert "+5.2%" in prompt_content  # 7-day positive
            assert "-2.3%" in prompt_content  # 30-day negative
            assert "+15.7%" in prompt_content  # 60-day positive
            assert "90-day" not in prompt_content  # None value should be skipped