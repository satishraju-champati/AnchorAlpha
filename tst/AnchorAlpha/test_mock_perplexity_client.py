"""
Unit tests for Mock Perplexity client.
"""

import pytest
from unittest.mock import patch
import time

from AnchorAlpha.api.mock_perplexity_client import MockPerplexityClient


class TestMockPerplexityClient:
    """Test cases for MockPerplexityClient."""
    
    def test_client_initialization(self):
        """Test mock client initialization."""
        client = MockPerplexityClient()
        assert client.api_key == "mock_key"
        
        client_with_key = MockPerplexityClient(api_key="test_key")
        assert client_with_key.api_key == "test_key"
    
    def test_classify_momentum_high_positive(self):
        """Test momentum classification for high positive momentum."""
        client = MockPerplexityClient()
        momentum_data = {"7-day": 0.15, "30-day": 0.12}
        
        classification = client._classify_momentum(momentum_data)
        assert classification == "high_positive"
    
    def test_classify_momentum_moderate_positive(self):
        """Test momentum classification for moderate positive momentum."""
        client = MockPerplexityClient()
        momentum_data = {"7-day": 0.05, "30-day": 0.04}
        
        classification = client._classify_momentum(momentum_data)
        assert classification == "moderate_positive"
    
    def test_classify_momentum_mixed(self):
        """Test momentum classification for mixed momentum."""
        client = MockPerplexityClient()
        momentum_data = {"7-day": 0.01, "30-day": -0.01}
        
        classification = client._classify_momentum(momentum_data)
        assert classification == "mixed"
    
    def test_classify_momentum_moderate_negative(self):
        """Test momentum classification for moderate negative momentum."""
        client = MockPerplexityClient()
        momentum_data = {"7-day": -0.05, "30-day": -0.06}
        
        classification = client._classify_momentum(momentum_data)
        assert classification == "moderate_negative"
    
    def test_classify_momentum_high_negative(self):
        """Test momentum classification for high negative momentum."""
        client = MockPerplexityClient()
        momentum_data = {"7-day": -0.15, "30-day": -0.12}
        
        classification = client._classify_momentum(momentum_data)
        assert classification == "high_negative"
    
    def test_classify_momentum_with_none_values(self):
        """Test momentum classification with None values."""
        client = MockPerplexityClient()
        momentum_data = {"7-day": 0.05, "30-day": None, "60-day": 0.04}
        
        classification = client._classify_momentum(momentum_data)
        assert classification == "moderate_positive"
    
    def test_classify_momentum_all_none(self):
        """Test momentum classification with all None values."""
        client = MockPerplexityClient()
        momentum_data = {"7-day": None, "30-day": None}
        
        classification = client._classify_momentum(momentum_data)
        assert classification == "mixed"
    
    def test_get_timeframe_description(self):
        """Test timeframe description generation."""
        client = MockPerplexityClient()
        
        # Single significant timeframe
        momentum_data = {"7-day": 0.05, "30-day": 0.01}
        description = client._get_timeframe_description(momentum_data)
        assert "7-day" in description
        
        # Multiple significant timeframes
        momentum_data = {"7-day": 0.05, "30-day": 0.04, "60-day": 0.01}
        description = client._get_timeframe_description(momentum_data)
        assert "7-day" in description and ("30-day" in description or "60-day" in description)
    
    def test_get_momentum_description(self):
        """Test momentum strength description."""
        client = MockPerplexityClient()
        
        # Exceptional momentum
        momentum_data = {"7-day": 0.20}
        description = client._get_momentum_description(momentum_data)
        assert description == "exceptional"
        
        # Strong momentum
        momentum_data = {"7-day": 0.10}
        description = client._get_momentum_description(momentum_data)
        assert description == "strong"
        
        # Moderate momentum
        momentum_data = {"7-day": 0.05}
        description = client._get_momentum_description(momentum_data)
        assert description == "moderate"
        
        # Modest momentum
        momentum_data = {"7-day": 0.02}
        description = client._get_momentum_description(momentum_data)
        assert description == "modest"
    
    @patch('time.sleep')
    def test_generate_stock_summary(self, mock_sleep):
        """Test stock summary generation."""
        client = MockPerplexityClient()
        
        momentum_data = {
            "7-day": 0.05,
            "30-day": 0.08,
            "60-day": None
        }
        
        summary = client.generate_stock_summary("AAPL", "Apple Inc.", momentum_data)
        
        assert isinstance(summary, str)
        assert len(summary) > 50  # Should be a substantial summary
        assert "Apple Inc." in summary
        mock_sleep.assert_called_once_with(0.1)
    
    @patch('time.sleep')
    def test_generate_batch_summaries(self, mock_sleep):
        """Test batch summary generation."""
        client = MockPerplexityClient()
        
        stocks_data = [
            {
                "ticker": "AAPL",
                "company_name": "Apple Inc.",
                "momentum_data": {"7-day": 0.05, "30-day": 0.08}
            },
            {
                "ticker": "MSFT",
                "company_name": "Microsoft Corporation",
                "momentum_data": {"7-day": 0.03, "30-day": 0.06}
            }
        ]
        
        summaries = client.generate_batch_summaries(stocks_data)
        
        assert len(summaries) == 2
        assert "AAPL" in summaries
        assert "MSFT" in summaries
        assert "Apple Inc." in summaries["AAPL"]
        assert "Microsoft Corporation" in summaries["MSFT"]
        
        # Should have called sleep for each stock (both in batch and individual calls)
        assert mock_sleep.call_count >= 2
    
    def test_generate_batch_summaries_missing_data(self):
        """Test batch summary generation with missing data."""
        client = MockPerplexityClient()
        
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
    
    @patch('time.sleep')
    def test_test_api_connection(self, mock_sleep):
        """Test mock API connection test."""
        client = MockPerplexityClient()
        
        result = client.test_api_connection()
        
        assert result is True
        mock_sleep.assert_called_once_with(0.1)
    
    def test_summary_templates_exist(self):
        """Test that all required summary templates exist."""
        client = MockPerplexityClient()
        
        required_patterns = ["high_positive", "moderate_positive", "mixed", 
                           "moderate_negative", "high_negative"]
        
        for pattern in required_patterns:
            assert pattern in client.SUMMARY_TEMPLATES
            assert len(client.SUMMARY_TEMPLATES[pattern]) > 0
    
    def test_catalysts_and_strengths_exist(self):
        """Test that catalyst and strength lists are populated."""
        client = MockPerplexityClient()
        
        assert len(client.CATALYSTS) > 10
        assert len(client.STRENGTHS) > 10
        
        # Check that they're all strings
        for catalyst in client.CATALYSTS:
            assert isinstance(catalyst, str)
            assert len(catalyst) > 5
        
        for strength in client.STRENGTHS:
            assert isinstance(strength, str)
            assert len(strength) > 5
    
    def test_summary_quality(self):
        """Test that generated summaries are of good quality."""
        client = MockPerplexityClient()
        
        momentum_data = {"7-day": 0.08, "30-day": 0.05}
        summary = client.generate_stock_summary("AAPL", "Apple Inc.", momentum_data)
        
        # Quality checks
        assert len(summary) > 100  # Substantial length
        assert len(summary) < 500  # Not too long
        assert "Apple Inc." in summary  # Contains company name
        assert summary.count('.') >= 1  # At least one complete sentence
        assert not summary.startswith(' ')  # No leading whitespace
        assert not summary.endswith(' ')  # No trailing whitespace