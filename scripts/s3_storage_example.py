#!/usr/bin/env python3
"""
Example script demonstrating S3 data storage functionality.

This script shows how to use the S3DataStorage and MomentumDataPipeline
classes to store and retrieve momentum screening data.
"""

import sys
import os
from datetime import date

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from AnchorAlpha.models import Stock
from AnchorAlpha.storage.s3_client import S3DataStorage
from AnchorAlpha.storage.data_pipeline import MomentumDataPipeline


def create_sample_stocks():
    """Create sample stock data for demonstration."""
    return [
        Stock(
            ticker="AAPL",
            company_name="Apple Inc.",
            current_price=150.25,
            market_cap=2400000000000,  # $2.4T
            momentum_7d=0.0523,
            momentum_30d=0.1245,
            momentum_60d=0.0876,
            momentum_90d=0.1567,
            ai_summary="Apple shares surged on strong iPhone sales and services growth"
        ),
        Stock(
            ticker="MSFT",
            company_name="Microsoft Corporation",
            current_price=300.50,
            market_cap=2200000000000,  # $2.2T
            momentum_7d=0.0312,
            momentum_30d=0.0987,
            momentum_60d=0.1234,
            momentum_90d=0.0876,
            ai_summary="Microsoft benefits from cloud computing expansion"
        ),
        Stock(
            ticker="GOOGL",
            company_name="Alphabet Inc.",
            current_price=120.75,
            market_cap=1500000000000,  # $1.5T
            momentum_7d=0.0234,
            momentum_30d=0.0654,
            momentum_60d=0.0987,
            momentum_90d=0.1123,
            ai_summary="Google's AI initiatives drive investor confidence"
        ),
        Stock(
            ticker="TSLA",
            company_name="Tesla Inc.",
            current_price=200.00,
            market_cap=600000000000,  # $600B
            momentum_7d=0.0876,
            momentum_30d=0.1543,
            momentum_60d=0.0432,
            momentum_90d=0.0765,
            ai_summary="Tesla's autonomous driving progress boosts stock price"
        ),
        Stock(
            ticker="NVDA",
            company_name="NVIDIA Corporation",
            current_price=450.00,
            market_cap=1100000000000,  # $1.1T
            momentum_7d=0.1234,
            momentum_30d=0.0876,
            momentum_60d=0.1567,
            momentum_90d=0.0543,
            ai_summary="NVIDIA leads AI chip market with strong demand"
        )
    ]


def demonstrate_s3_storage():
    """Demonstrate S3 storage functionality."""
    print("=== S3 Data Storage Example ===\n")
    
    # Note: This example uses mock data and won't actually connect to AWS
    # In production, ensure AWS credentials are configured
    
    try:
        # Create sample data
        stocks = create_sample_stocks()
        print(f"Created {len(stocks)} sample stocks")
        
        # Initialize the data pipeline
        # In production, this would use real AWS credentials
        print("\nInitializing data pipeline...")
        pipeline = MomentumDataPipeline()
        
        # Organize stocks by tier and timeframe
        print("\nOrganizing stocks by tier and timeframe...")
        organized_data = pipeline._organize_stocks_by_tier_and_timeframe(stocks)
        
        # Display organization results
        for tier, timeframe_data in organized_data.items():
            print(f"\n{tier} tier:")
            for timeframe, tier_stocks in timeframe_data.items():
                if tier_stocks:
                    print(f"  {timeframe}-day: {len(tier_stocks)} stocks")
                    for i, stock in enumerate(tier_stocks[:3], 1):  # Show top 3
                        momentum = stock.get_momentum(int(timeframe))
                        print(f"    {i}. {stock.ticker} - {momentum:.2%} momentum")
        
        # Demonstrate JSON serialization
        print("\n=== JSON Serialization Example ===")
        
        # This would normally upload to S3, but we'll just show the serialization
        market_date = date.today().strftime("%Y-%m-%d")
        
        # Create a mock S3 storage for demonstration
        from unittest.mock import Mock
        mock_s3 = Mock()
        mock_s3.upload_momentum_data.return_value = True
        
        # Create a real S3DataStorage instance for serialization demonstration
        # but don't actually connect to AWS
        from AnchorAlpha.storage.s3_client import S3DataStorage
        demo_s3 = S3DataStorage.__new__(S3DataStorage)  # Create without __init__
        demo_s3.bucket_name = "anchoralpha-data"
        demo_s3.region = "us-east-1"
        demo_s3.key_prefix = "momentum-data"
        
        pipeline_with_demo = MomentumDataPipeline(s3_storage=demo_s3)
        
        # Serialize the data (this shows what would be uploaded to S3)
        json_data = demo_s3._serialize_stock_data(organized_data, market_date)
        
        print(f"Market Date: {json_data['market_date']}")
        print(f"Generated At: {json_data['generated_at']}")
        print(f"Data Version: {json_data['data_version']}")
        print(f"Number of tiers: {len(json_data['tiers'])}")
        
        # Show sample serialized stock data
        if "1T_plus" in json_data["tiers"] and "7_day" in json_data["tiers"]["1T_plus"]:
            sample_stock = json_data["tiers"]["1T_plus"]["7_day"][0]
            print(f"\nSample serialized stock:")
            print(f"  Ticker: {sample_stock['ticker']}")
            print(f"  Company: {sample_stock['company_name']}")
            print(f"  Price: ${sample_stock['current_price']:.2f}")
            print(f"  Market Cap: ${sample_stock['market_cap']:,}")
            print(f"  7-day Momentum: {sample_stock['momentum_7d']:.2%}")
            if sample_stock['ai_summary']:
                print(f"  AI Summary: {sample_stock['ai_summary'][:50]}...")
        
        print("\n=== Storage Operations Example ===")
        
        # Simulate successful storage
        print("✓ Data would be uploaded to S3 with:")
        print(f"  - Bucket: anchoralpha-data")
        print(f"  - Key: momentum-data/momentum-data-{market_date}.json")
        print(f"  - Encryption: AES256")
        print(f"  - Content-Type: application/json")
        
        # Show what retrieval would look like
        print(f"\n✓ Data could be retrieved using:")
        print(f"  pipeline.retrieve_momentum_data('{market_date}')")
        
        print(f"\n✓ Available dates could be listed using:")
        print(f"  pipeline.get_available_data_dates()")
        
        print(f"\n✓ Data validation could be performed using:")
        print(f"  pipeline.validate_stored_data('{market_date}')")
        
        print("\n=== Example Complete ===")
        print("This demonstrates the S3 storage functionality without requiring AWS credentials.")
        print("In production, configure AWS credentials and the system will store data in S3.")
        
    except Exception as e:
        print(f"Error in demonstration: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = demonstrate_s3_storage()
    sys.exit(0 if success else 1)