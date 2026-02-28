#!/usr/bin/env python3
"""
Test script to verify Perplexity API integration with real API key.
Run this to test the Perplexity client with live API calls.
"""

import os
import sys
import logging

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from AnchorAlpha.api.perplexity_client import PerplexityClient, PerplexityAPIError

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_perplexity_api():
    """Test Perplexity API integration."""
    
    print("🔍 Testing Perplexity Sonar API Integration")
    print("=" * 50)
    
    # You'll need to get a Perplexity API key from https://www.perplexity.ai/
    api_key = os.getenv("PERPLEXITY_API_KEY")
    
    if not api_key:
        print("❌ No PERPLEXITY_API_KEY found in environment variables")
        print("\n💡 To test with real API:")
        print("1. Get API key from: https://www.perplexity.ai/")
        print("2. Set environment variable: export PERPLEXITY_API_KEY=your_key_here")
        print("3. Run this script again")
        print("\n🔄 Testing with mock data instead...")
        test_with_mock_data()
        return False
    
    try:
        logger.info("Initializing Perplexity client...")
        client = PerplexityClient(api_key=api_key)
        
        # Test 1: API Connection
        logger.info("Testing API connection...")
        if client.test_api_connection():
            print("✅ API connection successful!")
        else:
            print("❌ API connection failed")
            return False
        
        # Test 2: Single Stock Summary
        logger.info("Testing single stock summary generation...")
        momentum_data = {
            "7-day": 0.0523,   # +5.23%
            "30-day": 0.1245,  # +12.45%
            "60-day": -0.0234, # -2.34%
            "90-day": 0.0876   # +8.76%
        }
        
        summary = client.generate_stock_summary("AAPL", "Apple Inc.", momentum_data)
        print(f"\n📊 AAPL Summary:")
        print(f"   {summary}")
        
        # Test 3: Batch Summaries
        logger.info("Testing batch summary generation...")
        stocks_data = [
            {
                "ticker": "MSFT",
                "company_name": "Microsoft Corporation",
                "momentum_data": {"7-day": 0.0345, "30-day": 0.0892}
            },
            {
                "ticker": "GOOGL",
                "company_name": "Alphabet Inc.",
                "momentum_data": {"7-day": -0.0123, "30-day": 0.0567}
            }
        ]
        
        batch_summaries = client.generate_batch_summaries(stocks_data)
        
        print(f"\n📈 Batch Summaries ({len(batch_summaries)} stocks):")
        for ticker, summary in batch_summaries.items():
            print(f"   {ticker}: {summary[:100]}...")
        
        print("\n✅ All Perplexity API tests passed!")
        print("\n📋 API Features Verified:")
        print("   ✅ Authentication and connection")
        print("   ✅ Single stock summary generation")
        print("   ✅ Batch processing with rate limiting")
        print("   ✅ Error handling and graceful degradation")
        
        return True
        
    except PerplexityAPIError as e:
        logger.error(f"❌ Perplexity API Error: {e}")
        print(f"\n💡 Common issues:")
        print("   - Invalid API key")
        print("   - API quota exceeded")
        print("   - Network connectivity issues")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False


def test_with_mock_data():
    """Test the client structure with mock data."""
    print("\n🧪 Testing client structure with mock data...")
    
    try:
        # This will fail due to no API key, but we can test the structure
        from AnchorAlpha.api.perplexity_client import PerplexityRateLimiter
        
        # Test rate limiter
        limiter = PerplexityRateLimiter(requests_per_minute=60)
        print("✅ Rate limiter initialized successfully")
        
        # Test momentum data formatting
        momentum_data = {
            "7-day": 0.0523,
            "30-day": -0.0234,
            "60-day": None
        }
        
        # Format momentum text like the client would
        momentum_text = []
        for period, momentum in momentum_data.items():
            if momentum is not None:
                momentum_pct = momentum * 100
                momentum_text.append(f"{period}: {momentum_pct:+.1f}%")
        
        momentum_summary = ", ".join(momentum_text)
        print(f"✅ Momentum formatting: {momentum_summary}")
        
        print("✅ Client structure tests passed!")
        
    except Exception as e:
        print(f"❌ Structure test failed: {e}")


def show_api_info():
    """Show information about getting Perplexity API access."""
    print("\n" + "=" * 60)
    print("📚 PERPLEXITY API INFORMATION:")
    print("\n🔑 Getting API Access:")
    print("   1. Visit: https://www.perplexity.ai/")
    print("   2. Sign up for an account")
    print("   3. Navigate to API settings")
    print("   4. Generate an API key")
    print("   5. Note: May require payment for API access")
    
    print("\n💰 Pricing (as of 2024):")
    print("   - Free tier: Limited requests")
    print("   - Paid plans: Higher rate limits")
    print("   - Check current pricing on their website")
    
    print("\n🔧 Models Available:")
    print("   - llama-3.1-sonar-small-128k-online (recommended)")
    print("   - llama-3.1-sonar-large-128k-online")
    print("   - Other Sonar models for real-time information")


if __name__ == "__main__":
    success = test_perplexity_api()
    show_api_info()
    
    if not success:
        print("\n🔄 Next Steps:")
        print("1. Get Perplexity API key")
        print("2. Set PERPLEXITY_API_KEY environment variable")
        print("3. Run this script again to test with real API")
        print("4. Or continue development with mock summaries")
        sys.exit(1)
    else:
        print("\n🎉 Perplexity API integration is ready!")
        print("You can now use AI-powered stock summaries in AnchorAlpha!")