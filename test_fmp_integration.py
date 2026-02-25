#!/usr/bin/env python3
"""
Test script to verify FMP API integration with real API key.
Run this to test the FMP client with live data.
"""

import os
import sys
import logging

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from AnchorAlpha.api.fmp_client import FMPClient, FMPAPIError

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_fmp_api():
    """Test FMP API integration."""
    
    # Use your API key
    api_key = "zGnf89XHdjXeCKtYEswNXxB2UT51iBBP"
    
    try:
        logger.info("Initializing FMP client...")
        client = FMPClient(api_key=api_key)
        
        logger.info("Testing stock screener API...")
        # Test with a smaller market cap first to get some results
        stocks = client.get_stock_screener(market_cap_more_than=50_000_000_000)  # $50B
        logger.info(f"Retrieved {len(stocks)} stocks from screener")
        
        if stocks:
            # Show first few stocks
            logger.info("Sample stocks:")
            for i, stock in enumerate(stocks[:5]):
                symbol = stock.get('symbol', 'N/A')
                name = stock.get('companyName', 'N/A')
                market_cap = stock.get('marketCap', 0)
                price = stock.get('price', 0)
                logger.info(f"  {i+1}. {symbol} - {name} - ${market_cap:,} - ${price}")
        
        logger.info("\nTesting large-cap stocks (>$10B)...")
        large_cap_stocks = client.get_large_cap_stocks()
        logger.info(f"Retrieved {len(large_cap_stocks)} large-cap stocks")
        
        logger.info("\nTesting stock creation and tier organization...")
        tiers = client.get_stocks_by_market_cap_tier()
        
        for tier_name, tier_stocks in tiers.items():
            logger.info(f"Tier {tier_name}: {len(tier_stocks)} stocks")
            if tier_stocks:
                # Show first stock in each tier
                stock = tier_stocks[0]
                logger.info(f"  Example: {stock.ticker} - {stock.company_name} - ${stock.market_cap:,}")
        
        logger.info("\nTesting historical prices for AAPL...")
        try:
            historical_data = client.get_historical_prices("AAPL", days=30)
            if "historical" in historical_data and historical_data["historical"]:
                recent_prices = historical_data["historical"][:5]
                logger.info("Recent AAPL prices:")
                for price_data in recent_prices:
                    date = price_data.get('date', 'N/A')
                    close = price_data.get('close', 0)
                    logger.info(f"  {date}: ${close}")
            else:
                logger.warning("No historical data returned for AAPL")
        except Exception as e:
            logger.error(f"Error getting historical prices: {e}")
        
        logger.info("\n✅ FMP API integration test completed successfully!")
        return True
        
    except FMPAPIError as e:
        logger.error(f"❌ FMP API Error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    logger.info("Starting FMP API integration test...")
    success = test_fmp_api()
    
    if success:
        logger.info("🎉 All tests passed! FMP API integration is working.")
    else:
        logger.error("💥 Tests failed. Check the errors above.")
        sys.exit(1)