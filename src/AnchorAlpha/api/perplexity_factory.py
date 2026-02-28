"""
Factory for creating Perplexity clients - automatically chooses between real and mock clients.
"""

import os
import logging
from typing import Union

logger = logging.getLogger(__name__)


def create_perplexity_client(api_key: str = None, force_mock: bool = False) -> Union['PerplexityClient', 'MockPerplexityClient']:
    """
    Create appropriate Perplexity client based on API key availability.
    
    Args:
        api_key: Optional API key. If not provided, will check environment variables.
        force_mock: If True, always return mock client regardless of API key availability.
        
    Returns:
        PerplexityClient if API key is available, MockPerplexityClient otherwise.
    """
    
    if force_mock:
        logger.info("Using MockPerplexityClient (forced)")
        from .mock_perplexity_client import MockPerplexityClient
        return MockPerplexityClient(api_key="mock_key")
    
    # Check for API key
    effective_api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
    
    if effective_api_key and effective_api_key != "your_perplexity_api_key_here":
        try:
            logger.info("Attempting to use real PerplexityClient")
            from .perplexity_client import PerplexityClient
            
            # Test the client quickly
            client = PerplexityClient(api_key=effective_api_key)
            
            # Quick connection test (optional - can be disabled for faster startup)
            # if client.test_api_connection():
            #     logger.info("Real PerplexityClient connection verified")
            #     return client
            # else:
            #     logger.warning("PerplexityClient connection failed, falling back to mock")
            
            logger.info("Using real PerplexityClient")
            return client
            
        except Exception as e:
            logger.warning(f"Failed to initialize real PerplexityClient: {e}")
            logger.info("Falling back to MockPerplexityClient")
    else:
        logger.info("No valid Perplexity API key found, using MockPerplexityClient")
    
    # Fall back to mock client
    from .mock_perplexity_client import MockPerplexityClient
    return MockPerplexityClient(api_key="mock_key")


def get_client_info(client) -> dict:
    """Get information about the current client type."""
    client_type = type(client).__name__
    
    if "Mock" in client_type:
        return {
            "type": "mock",
            "name": "MockPerplexityClient",
            "description": "Mock client for development - generates realistic summaries",
            "cost": "Free",
            "rate_limit": "No limit"
        }
    else:
        return {
            "type": "real",
            "name": "PerplexityClient", 
            "description": "Real Perplexity Sonar API client",
            "cost": "Paid API usage",
            "rate_limit": "60 requests/minute"
        }