"""
Example usage of the Streamlit data loader and S3 integration.
"""

import logging
from datetime import datetime
from data_loader import StreamlitDataLoader, get_data_loader
from cache_manager import get_cache_manager, get_cached_data_loader
from data_transforms import DataTransformer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_data_loading():
    """Example of loading and transforming momentum data."""
    print("=== AnchorAlpha Streamlit Data Loader Example ===\n")
    
    try:
        # Get data loader instance
        data_loader = get_data_loader()
        print("✓ Data loader initialized")
        
        # Load latest momentum data
        print("Loading latest momentum data from S3...")
        raw_data = data_loader.load_latest_momentum_data()
        
        if raw_data:
            print(f"✓ Loaded data for market date: {raw_data.get('market_date')}")
            print(f"  Generated at: {raw_data.get('generated_at')}")
            print(f"  Data version: {raw_data.get('data_version')}")
            
            # Transform data for UI
            print("\nTransforming data for UI display...")
            transformed_data = data_loader.transform_data_for_ui(raw_data)
            
            # Display summary
            summary = transformed_data.get('summary', {})
            print(f"✓ Data transformation complete")
            print(f"  Total stocks: {summary.get('total_stocks', 0)}")
            print(f"  Total tiers: {summary.get('total_tiers', 0)}")
            print(f"  Timeframes: {', '.join(summary.get('timeframes', []))}")
            
            # Show tier breakdown
            print("\n--- Tier Breakdown ---")
            for tier_key, tier_data in transformed_data.get('tiers', {}).items():
                tier_name = data_loader.get_tier_display_name(tier_key)
                print(f"\n{tier_name}:")
                
                for timeframe, stocks in tier_data.get('timeframes', {}).items():
                    timeframe_name = data_loader.get_timeframe_display_name(timeframe)
                    print(f"  {timeframe_name}: {len(stocks)} stocks")
                    
                    # Show top 3 stocks for this timeframe
                    for i, stock in enumerate(stocks[:3]):
                        print(f"    {i+1}. {stock['ticker']} ({stock['company_name']}) - {stock['momentum_display']}")
            
            # Demonstrate data transformation utilities
            print("\n--- Data Transformation Examples ---")
            transformer = DataTransformer()
            
            # Get stocks from first tier and timeframe
            first_tier = list(transformed_data['tiers'].keys())[0]
            first_timeframe = list(transformed_data['tiers'][first_tier]['timeframes'].keys())[0]
            sample_stocks = transformed_data['tiers'][first_tier]['timeframes'][first_timeframe]
            
            if sample_stocks:
                # Create DataFrame
                df = transformer.create_stock_dataframe(sample_stocks, first_timeframe)
                print(f"✓ Created DataFrame with {len(df)} stocks")
                
                # Filter stocks with AI summaries
                stocks_with_summaries = transformer.filter_stocks_by_criteria(
                    sample_stocks, has_summary=True
                )
                print(f"✓ Found {len(stocks_with_summaries)} stocks with AI summaries")
                
                # Calculate momentum distribution
                distribution = transformer.calculate_momentum_distribution(sample_stocks)
                if distribution:
                    print(f"✓ Momentum distribution: avg={distribution['mean']:.3f}, "
                          f"max={distribution['max']:.3f}, min={distribution['min']:.3f}")
        else:
            print("✗ No momentum data available")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        logger.error(f"Example failed: {e}")


def example_caching():
    """Example of caching functionality."""
    print("\n=== Caching Example ===\n")
    
    try:
        # Get cache manager
        cache_manager = get_cache_manager()
        print("✓ Cache manager initialized")
        
        # Get cached data loader
        cached_loader = get_cached_data_loader()
        print("✓ Cached data loader initialized")
        
        # Example cached operation
        def expensive_operation():
            print("  Performing expensive operation...")
            return {"result": "expensive_data", "timestamp": datetime.now().isoformat()}
        
        print("First call (should execute operation):")
        result1 = cached_loader.cached_load("test_key", expensive_operation, ttl=60)
        print(f"✓ Result: {result1['result']}")
        
        print("\nSecond call (should use cache):")
        result2 = cached_loader.cached_load("test_key", expensive_operation, ttl=60)
        print(f"✓ Result: {result2['result']} (cached)")
        
        # Cache statistics
        stats = cache_manager.get_cache_stats()
        print(f"\n--- Cache Statistics ---")
        print(f"Memory entries: {stats['memory_entries']}")
        print(f"Persistent entries: {stats['persistent_entries']}")
        print(f"Total size: {stats['total_size_mb']:.2f} MB")
        
    except Exception as e:
        print(f"✗ Caching error: {e}")
        logger.error(f"Caching example failed: {e}")


def example_error_handling():
    """Example of error handling."""
    print("\n=== Error Handling Example ===\n")
    
    try:
        data_loader = get_data_loader()
        
        # Simulate an error
        test_error = Exception("Test connection error")
        error_info = data_loader.handle_data_loading_error(test_error)
        
        print("✓ Error handling example:")
        print(f"  Error type: {error_info['error_type']}")
        print(f"  Error message: {error_info['error_message']}")
        print(f"  Suggestions: {', '.join(error_info['suggestions'])}")
        
        # Test data freshness validation
        fresh_data = {"generated_at": datetime.now().isoformat() + "Z"}
        is_fresh = data_loader.validate_data_freshness(fresh_data)
        print(f"✓ Data freshness check: {'Fresh' if is_fresh else 'Stale'}")
        
    except Exception as e:
        print(f"✗ Error handling example failed: {e}")


if __name__ == "__main__":
    # Run examples
    example_data_loading()
    example_caching()
    example_error_handling()
    
    print("\n=== Example Complete ===")
    print("The Streamlit data loader is ready for integration with the UI components.")