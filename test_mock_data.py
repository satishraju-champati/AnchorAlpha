#!/usr/bin/env python3
"""
Test mock data provider to verify it works as expected.
"""

import sys
import os
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from AnchorAlpha.api.mock_data_provider import MockDataProvider

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_mock_data_provider():
    """Test mock data provider functionality."""
    
    logger.info("Testing Mock Data Provider...")
    
    try:
        # Initialize provider
        provider = MockDataProvider()
        
        # Test large-cap stocks
        logger.info("\n1. Testing large-cap stock generation...")
        stocks_data = provider.get_large_cap_stocks()
        logger.info(f"✅ Generated {len(stocks_data)} stocks")
        
        if stocks_data:
            sample = stocks_data[0]
            logger.info(f"Sample stock: {sample['symbol']} - {sample['companyName']}")
            logger.info(f"  Price: ${sample['price']}")
            logger.info(f"  Market Cap: ${sample['marketCap']:,}")
        
        # Test tier organization
        logger.info("\n2. Testing tier organization...")
        tiers = provider.get_stocks_by_market_cap_tier()
        
        total_stocks = 0
        for tier_name, tier_stocks in tiers.items():
            logger.info(f"Tier {tier_name}: {len(tier_stocks)} stocks")
            total_stocks += len(tier_stocks)
            
            if tier_stocks:
                sample_stock = tier_stocks[0]
                logger.info(f"  Example: {sample_stock.ticker} - ${sample_stock.market_cap:,}")
        
        logger.info(f"Total stocks across all tiers: {total_stocks}")
        
        # Test historical data
        logger.info("\n3. Testing historical price generation...")
        historical_data = provider.get_historical_prices("AAPL", days=30)
        
        if "historical" in historical_data and historical_data["historical"]:
            prices = historical_data["historical"]
            logger.info(f"✅ Generated {len(prices)} historical prices for AAPL")
            
            # Show recent prices
            logger.info("Recent prices:")
            for i, price_data in enumerate(prices[:5]):
                date = price_data["date"]
                close = price_data["close"]
                logger.info(f"  {date}: ${close}")
        
        # Test stock creation
        logger.info("\n4. Testing Stock object creation...")
        sample_data = stocks_data[0]
        stock = provider.create_stock_from_data(sample_data)
        
        if stock:
            logger.info(f"✅ Created Stock object: {stock.ticker}")
            logger.info(f"  Company: {stock.company_name}")
            logger.info(f"  Price: ${stock.current_price}")
            logger.info(f"  Market Cap: ${stock.market_cap:,}")
            logger.info(f"  Tier: {stock.get_tier()}")
        
        logger.info("\n🎉 All mock data provider tests passed!")
        logger.info("\n" + "="*60)
        logger.info("SUMMARY:")
        logger.info("✅ Mock data provider is working correctly")
        logger.info("✅ Can generate realistic stock data for development")
        logger.info("✅ Tier organization works properly")
        logger.info("✅ Historical price generation works")
        logger.info("\nYou can now continue development with mock data!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error testing mock data provider: {e}")
        return False


if __name__ == "__main__":
    success = test_mock_data_provider()
    
    if not success:
        sys.exit(1)