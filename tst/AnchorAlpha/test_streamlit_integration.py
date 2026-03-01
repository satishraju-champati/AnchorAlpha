"""
Integration tests for Streamlit data loading pipeline.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import tempfile
import boto3
from moto import mock_aws

from AnchorAlpha.streamlit_app.data_loader import StreamlitDataLoader, get_data_loader
from AnchorAlpha.streamlit_app.cache_manager import CacheManager, get_cache_manager
from AnchorAlpha.storage.s3_client import S3DataStorage


class TestStreamlitS3Integration:
    """Integration tests for Streamlit S3 data loading."""
    
    @pytest.fixture
    def sample_momentum_data(self):
        """Sample momentum data for S3 testing."""
        return {
            "generated_at": "2026-02-21T16:30:00Z",
            "market_date": "2026-02-21",
            "data_version": "1.0",
            "tiers": {
                "100B_200B": {
                    "7_day": [
                        {
                            "ticker": "AAPL",
                            "company_name": "Apple Inc.",
                            "current_price": 150.25,
                            "market_cap": 150000000000,
                            "momentum_7d": 0.0523,
                            "momentum_30d": 0.1245,
                            "momentum_60d": 0.0876,
                            "momentum_90d": 0.1567,
                            "ai_summary": "Apple shares surged on strong iPhone sales...",
                            "tier": "100B_200B"
                        },
                        {
                            "ticker": "GOOGL",
                            "company_name": "Alphabet Inc.",
                            "current_price": 2800.75,
                            "market_cap": 180000000000,
                            "momentum_7d": 0.0345,
                            "momentum_30d": 0.0987,
                            "momentum_60d": 0.0654,
                            "momentum_90d": 0.1234,
                            "ai_summary": "Google parent company benefits from AI investments...",
                            "tier": "100B_200B"
                        }
                    ],
                    "30_day": [
                        {
                            "ticker": "AAPL",
                            "company_name": "Apple Inc.",
                            "current_price": 150.25,
                            "market_cap": 150000000000,
                            "momentum_7d": 0.0523,
                            "momentum_30d": 0.1245,
                            "momentum_60d": 0.0876,
                            "momentum_90d": 0.1567,
                            "ai_summary": "Apple shares surged on strong iPhone sales...",
                            "tier": "100B_200B"
                        }
                    ]
                },
                "200B_500B": {
                    "7_day": [
                        {
                            "ticker": "TSLA",
                            "company_name": "Tesla Inc.",
                            "current_price": 850.50,
                            "market_cap": 270000000000,
                            "momentum_7d": 0.0789,
                            "momentum_30d": 0.1456,
                            "momentum_60d": 0.0987,
                            "momentum_90d": 0.1789,
                            "ai_summary": "Tesla stock rallies on strong delivery numbers...",
                            "tier": "200B_500B"
                        }
                    ]
                }
            }
        }
    
    @mock_aws
    def test_end_to_end_data_loading(self, sample_momentum_data):
        """Test complete end-to-end data loading from S3."""
        # Setup mock S3 environment
        bucket_name = "test-anchoralpha-data"
        region = "us-east-1"
        
        # Create S3 bucket and upload test data
        s3_client = boto3.client('s3', region_name=region)
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Upload sample data
        s3_key = "momentum-data/momentum-data-2026-02-21.json"
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=json.dumps(sample_momentum_data),
            ContentType='application/json'
        )
        
        # Test data loading
        with patch.dict('os.environ', {
            'S3_BUCKET': bucket_name,
            'AWS_REGION': region
        }):
            # Also patch the Config class
            with patch('AnchorAlpha.streamlit_app.data_loader.Config') as mock_config:
                mock_config.S3_BUCKET = bucket_name
                mock_config.AWS_REGION = region
                mock_config.S3_KEY_PREFIX = "momentum-data"
                
                # Create data loader
                with patch('streamlit.cache_data', lambda **kwargs: lambda func: func):
                    data_loader = StreamlitDataLoader()
                    
                    # Test loading latest data
                    result = data_loader.load_latest_momentum_data()
                    
                    assert result is not None
                    assert result['market_date'] == '2026-02-21'
                    assert 'tiers' in result
                    assert '100B_200B' in result['tiers']
                    assert '200B_500B' in result['tiers']
    
    @mock_aws
    def test_data_transformation_pipeline(self, sample_momentum_data):
        """Test complete data transformation pipeline."""
        # Setup S3 with test data
        bucket_name = "test-anchoralpha-data"
        region = "us-east-1"
        
        s3_client = boto3.client('s3', region_name=region)
        s3_client.create_bucket(Bucket=bucket_name)
        
        s3_key = "momentum-data/momentum-data-2026-02-21.json"
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=json.dumps(sample_momentum_data),
            ContentType='application/json'
        )
        
        with patch.dict('os.environ', {
            'S3_BUCKET': bucket_name,
            'AWS_REGION': region
        }):
            with patch('streamlit.cache_data', lambda **kwargs: lambda func: func):
                data_loader = StreamlitDataLoader()
                
                # Load and transform data
                raw_data = data_loader.load_latest_momentum_data()
                transformed_data = data_loader.transform_data_for_ui(raw_data)
                
                # Verify transformation
                assert 'metadata' in transformed_data
                assert 'tiers' in transformed_data
                assert 'summary' in transformed_data
                
                # Check tier data
                tier_100b = transformed_data['tiers']['100B_200B']
                assert 'timeframes' in tier_100b
                assert 'stats' in tier_100b
                
                # Check 7-day timeframe
                stocks_7d = tier_100b['timeframes']['7d']
                assert len(stocks_7d) == 2
                
                # Check stock transformation
                aapl_stock = next(s for s in stocks_7d if s['ticker'] == 'AAPL')
                assert aapl_stock['momentum_pct'] == 5.23
                assert aapl_stock['momentum_display'] == '+5.23%'
                assert aapl_stock['has_summary'] is True
                assert aapl_stock['market_cap_display'] == '$150.0B'
                
                # Check statistics
                stats_7d = tier_100b['stats']['7d']
                assert stats_7d['count'] == 2
                assert stats_7d['stocks_with_summaries'] == 2
                assert stats_7d['max_momentum'] == 0.0523
    
    def test_caching_integration(self):
        """Test caching integration with data loading."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = CacheManager(cache_dir=temp_dir)
            
            # Mock data loader function
            call_count = 0
            def mock_data_loader():
                nonlocal call_count
                call_count += 1
                return {'data': f'loaded_{call_count}', 'timestamp': datetime.now().isoformat()}
            
            # First call should load fresh data
            result1 = cache_manager.get('test_data')
            assert result1 is None
            
            cache_manager.set('test_data', mock_data_loader(), ttl=60)
            
            # Second call should return cached data
            result2 = cache_manager.get('test_data')
            assert result2 is not None
            assert result2['data'] == 'loaded_1'
            
            # Verify cache statistics
            stats = cache_manager.get_cache_stats()
            assert stats['memory_entries'] >= 1
    
    def test_error_handling_integration(self):
        """Test error handling in the complete pipeline."""
        with patch('streamlit.cache_data', lambda **kwargs: lambda func: func):
            # Create data loader with failing S3 client
            with patch('AnchorAlpha.streamlit_app.data_loader.S3DataStorage') as mock_s3:
                mock_s3_instance = Mock()
                mock_s3_instance.list_available_dates.side_effect = Exception("S3 connection failed")
                mock_s3.return_value = mock_s3_instance
                
                data_loader = StreamlitDataLoader()
                
                # Test error handling
                result = data_loader.load_latest_momentum_data()
                assert result is None
                
                # Test error information generation
                error = Exception("Test error")
                error_info = data_loader.handle_data_loading_error(error)
                
                assert error_info['error'] is True
                assert error_info['error_type'] == 'Exception'
                assert 'suggestions' in error_info
    
    def test_data_freshness_validation(self):
        """Test data freshness validation in pipeline."""
        with patch('streamlit.cache_data', lambda **kwargs: lambda func: func):
            data_loader = StreamlitDataLoader()
            
            # Test fresh data
            fresh_data = {
                'generated_at': datetime.now().isoformat() + 'Z',
                'market_date': '2026-02-21'
            }
            assert data_loader.validate_data_freshness(fresh_data) is True
            
            # Test stale data
            stale_time = datetime.now() - timedelta(hours=50)
            stale_data = {
                'generated_at': stale_time.isoformat() + 'Z',
                'market_date': '2026-02-19'
            }
            assert data_loader.validate_data_freshness(stale_data) is False
    
    @mock_aws
    def test_multiple_dates_handling(self):
        """Test handling multiple dates in S3."""
        bucket_name = "test-anchoralpha-data"
        region = "us-east-1"
        
        s3_client = boto3.client('s3', region_name=region)
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Upload data for multiple dates
        dates = ['2026-02-21', '2026-02-20', '2026-02-19']
        for i, date in enumerate(dates):
            data = {
                "generated_at": f"{date}T16:30:00Z",
                "market_date": date,
                "data_version": "1.0",
                "tiers": {"100B_200B": {"7_day": []}}
            }
            
            s3_key = f"momentum-data/momentum-data-{date}.json"
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=json.dumps(data),
                ContentType='application/json'
            )
        
        with patch.dict('os.environ', {
            'S3_BUCKET': bucket_name,
            'AWS_REGION': region
        }):
            with patch('streamlit.cache_data', lambda **kwargs: lambda func: func):
                data_loader = StreamlitDataLoader()
                
                # Test getting available dates
                available_dates = data_loader.get_available_dates()
                assert len(available_dates) == 3
                assert '2026-02-21' in available_dates
                
                # Test loading specific date
                specific_data = data_loader.load_momentum_data_by_date('2026-02-20')
                assert specific_data is not None
                assert specific_data['market_date'] == '2026-02-20'
    
    def test_streamlit_cache_decorators(self):
        """Test Streamlit cache decorator integration."""
        # Mock streamlit cache decorators
        cache_calls = []
        
        def mock_cache_data(**kwargs):
            def decorator(func):
                cache_calls.append(kwargs)
                return func
            return decorator
        
        def mock_cache_resource(**kwargs):
            def decorator(func):
                cache_calls.append(kwargs)
                return func
            return decorator
        
        with patch('streamlit.cache_data', mock_cache_data):
            with patch('streamlit.cache_resource', mock_cache_resource):
                # Import functions that use cache decorators
                from AnchorAlpha.streamlit_app.data_loader import get_data_loader
                from AnchorAlpha.streamlit_app.cache_manager import get_cache_manager
                
                # Verify cache decorators were applied
                loader = get_data_loader()
                cache_mgr = get_cache_manager()
                
                assert len(cache_calls) >= 2  # At least 2 cache decorator calls


class TestDataLoaderPerformance:
    """Performance tests for data loading operations."""
    
    def test_large_dataset_transformation(self):
        """Test transformation performance with large dataset."""
        # Create large dataset
        large_data = {
            "generated_at": "2026-02-21T16:30:00Z",
            "market_date": "2026-02-21",
            "data_version": "1.0",
            "tiers": {}
        }
        
        # Generate data for all tiers and timeframes
        tiers = ["100B_200B", "200B_500B", "500B_1T", "1T_plus"]
        timeframes = ["7_day", "30_day", "60_day", "90_day"]
        
        for tier in tiers:
            large_data["tiers"][tier] = {}
            for timeframe in timeframes:
                stocks = []
                for i in range(20):  # 20 stocks per tier/timeframe
                    stock = {
                        "ticker": f"STOCK{i:03d}",
                        "company_name": f"Company {i}",
                        "current_price": 100.0 + i,
                        "market_cap": 100000000000 + (i * 1000000000),
                        "momentum_7d": 0.01 + (i * 0.001),
                        "momentum_30d": 0.02 + (i * 0.001),
                        "momentum_60d": 0.015 + (i * 0.001),
                        "momentum_90d": 0.025 + (i * 0.001),
                        "ai_summary": f"Summary for stock {i}",
                        "tier": tier
                    }
                    stocks.append(stock)
                large_data["tiers"][tier][timeframe] = stocks
        
        # Test transformation performance
        import time
        
        with patch('streamlit.cache_data', lambda **kwargs: lambda func: func):
            data_loader = StreamlitDataLoader()
            
            start_time = time.time()
            transformed_data = data_loader.transform_data_for_ui(large_data)
            end_time = time.time()
            
            # Verify transformation completed
            assert 'tiers' in transformed_data
            assert len(transformed_data['tiers']) == 4
            
            # Performance should be reasonable (less than 1 second for this dataset)
            transformation_time = end_time - start_time
            assert transformation_time < 1.0, f"Transformation took {transformation_time:.2f} seconds"
    
    def test_cache_performance(self):
        """Test cache performance with multiple operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = CacheManager(cache_dir=temp_dir)
            
            # Test multiple cache operations
            import time
            
            start_time = time.time()
            
            # Set multiple cache entries
            for i in range(100):
                cache_manager.set(f'key_{i}', f'value_{i}', ttl=60, persist=True)
            
            # Get multiple cache entries
            for i in range(100):
                result = cache_manager.get(f'key_{i}')
                assert result == f'value_{i}'
            
            end_time = time.time()
            
            # Performance should be reasonable
            total_time = end_time - start_time
            assert total_time < 2.0, f"Cache operations took {total_time:.2f} seconds"


if __name__ == '__main__':
    pytest.main([__file__])