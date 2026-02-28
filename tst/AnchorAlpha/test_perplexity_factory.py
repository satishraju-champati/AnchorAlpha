"""
Unit tests for Perplexity client factory.
"""

import pytest
from unittest.mock import patch, Mock
import os

from AnchorAlpha.api.perplexity_factory import create_perplexity_client, get_client_info


class TestPerplexityFactory:
    """Test cases for Perplexity client factory."""
    
    def test_create_client_force_mock(self):
        """Test creating mock client when forced."""
        client = create_perplexity_client(force_mock=True)
        
        assert type(client).__name__ == "MockPerplexityClient"
        assert client.api_key == "mock_key"
    
    @patch.dict(os.environ, {}, clear=True)
    def test_create_client_no_api_key(self):
        """Test creating client with no API key available."""
        client = create_perplexity_client()
        
        assert type(client).__name__ == "MockPerplexityClient"
    
    @patch.dict(os.environ, {"PERPLEXITY_API_KEY": "your_perplexity_api_key_here"}, clear=True)
    def test_create_client_placeholder_api_key(self):
        """Test creating client with placeholder API key."""
        client = create_perplexity_client()
        
        # Should use mock client for placeholder key
        assert type(client).__name__ == "MockPerplexityClient"
    
    @patch.dict(os.environ, {"PERPLEXITY_API_KEY": "real_api_key_123"}, clear=True)
    def test_create_client_with_real_api_key(self):
        """Test creating client with real API key."""
        client = create_perplexity_client()
        
        # Should attempt to use real client
        assert type(client).__name__ == "PerplexityClient"
        assert client.api_key == "real_api_key_123"
    
    def test_create_client_with_explicit_api_key(self):
        """Test creating client with explicitly provided API key."""
        client = create_perplexity_client(api_key="explicit_key_456")
        
        assert type(client).__name__ == "PerplexityClient"
        assert client.api_key == "explicit_key_456"
    
    @patch('AnchorAlpha.api.perplexity_client.PerplexityClient')
    def test_create_client_real_client_initialization_fails(self, mock_perplexity_class):
        """Test fallback to mock when real client initialization fails."""
        mock_perplexity_class.side_effect = Exception("API initialization failed")
        
        client = create_perplexity_client(api_key="failing_key")
        
        # Should fall back to mock client
        assert type(client).__name__ == "MockPerplexityClient"
    
    def test_get_client_info_mock(self):
        """Test getting info for mock client."""
        from AnchorAlpha.api.mock_perplexity_client import MockPerplexityClient
        client = MockPerplexityClient()
        
        info = get_client_info(client)
        
        assert info["type"] == "mock"
        assert info["name"] == "MockPerplexityClient"
        assert "mock" in info["description"].lower()
        assert info["cost"] == "Free"
        assert "No limit" in info["rate_limit"]
    
    def test_get_client_info_real(self):
        """Test getting info for real client."""
        from AnchorAlpha.api.perplexity_client import PerplexityClient
        client = PerplexityClient(api_key="test_key")
        
        info = get_client_info(client)
        
        assert info["type"] == "real"
        assert info["name"] == "PerplexityClient"
        assert "real" in info["description"].lower() or "sonar" in info["description"].lower()
        assert "paid" in info["cost"].lower()
        assert "60" in info["rate_limit"]
    
    @patch.dict(os.environ, {"PERPLEXITY_API_KEY": ""}, clear=True)
    def test_create_client_empty_api_key(self):
        """Test creating client with empty API key."""
        client = create_perplexity_client()
        
        # Should use mock client for empty key
        assert type(client).__name__ == "MockPerplexityClient"
    
    def test_create_client_precedence(self):
        """Test that explicit API key takes precedence over environment variable."""
        with patch.dict(os.environ, {"PERPLEXITY_API_KEY": "env_key"}, clear=True):
            client = create_perplexity_client(api_key="explicit_key")
            
            assert client.api_key == "explicit_key"
    
    def test_factory_imports_work(self):
        """Test that factory can import both client types."""
        # This test ensures the imports in the factory function work
        mock_client = create_perplexity_client(force_mock=True)
        assert mock_client is not None
        
        real_client = create_perplexity_client(api_key="test_key")
        assert real_client is not None
        
        # They should be different types
        assert type(mock_client).__name__ != type(real_client).__name__