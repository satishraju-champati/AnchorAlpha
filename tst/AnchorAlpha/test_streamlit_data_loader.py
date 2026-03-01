"""
Unit tests for Streamlit data loader and S3 integration.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import tempfile
import os

from AnchorAlpha.streamlit_app.data_loader import StreamlitDataLoader
from AnchorAlpha.streamlit_app.cache_manager import CacheManager, CachedDataLoader
from AnchorAlpha.streamlit_app.data_transforms import DataTransformer


class TestStreamlitDataLoader:
    """Test cases for StreamlitDataLoader."""
    
    @pytest.fixture
    def mock_s3_client(self):
        """Mock S3 client for testing."""
        mock_client = Mock()
        mock_client.list_available_dates.return_value = ['2026-02-21', '2026-02-20']
        mock_client.download_momentum_data.return_value = self._get_sample_data()
        mock_client.validate_json_schema.return_value = True
        return mock_client
    
    @pytest.fixture
    def data_loader(self, mock_s3_client):
        """Create data loader with mocked S3 client."""
        with patch('AnchorAlpha.streamlit_app.data_loader.S3DataStorage') as mock_s3:
            mock_s3.return_value = mock_s3_client
            loader = StreamlitDataLoader()
            return loader
    
    def _get_sample_data(self):
        """Get sample momentum data for testing."""
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
                            "market_cap": 2400000000000,
                            "momentum_7d": 0.0523,
                            "momentum_30d": 0.1245,
                            "momentum_60d": 0.0876,
                            "momentum_90d": 0.1567,
                            "ai_summary": "Apple shares surged on strong iPhone sales...",
                            "tier": "100B_200B"
                        }
                    ]
                }
            }
        }
    
    def test_load_latest_momentum_data_success(self, data_loader):
        """Test successful loading of latest momentum data."""
        # Mock streamlit cache decorator
        with patch('streamlit.cache_data', lambda **kwargs: lambda func: func):
            result = data_loader.load_latest_momentum_data()
        
        assert result is not None
        assert result['market_date'] == '2026-02-21'
        assert 'tiers' in result
    
    def test_load_latest_momentum_data_no_data(self):
        """Test loading when no data is available."""
        # Create a fresh data loader with mocked S3 client
        with patch('AnchorAlpha.streamlit_app.data_loader.S3DataStorage') as mock_s3:
            mock_s3_instance = Mock()
            mock_s3_instance.list_available_dates.return_value = []
            mock_s3.return_value = mock_s3_instance
            
            with patch('streamlit.cache_data', lambda **kwargs: lambda func: func):
                data_loader = StreamlitDataLoader()
                result = data_loader.load_latest_momentum_data()
        
        assert result is None
    
    def test_load_latest_momentum_data_invalid_data(self):
        """Test loading when data is invalid."""
        # Create a fresh data loader with mocked S3 client
        with patch('AnchorAlpha.streamlit_app.data_loader.S3DataStorage') as mock_s3:
            mock_s3_instance = Mock()
            mock_s3_instance.list_available_dates.return_value = ['2026-02-21']
            mock_s3_instance.download_momentum_data.return_value = {'invalid': 'data'}
            mock_s3_instance.validate_json_schema.return_value = False
            mock_s3.return_value = mock_s3_instance
            
            with patch('streamlit.cache_data', lambda **kwargs: lambda func: func):
                data_loader = StreamlitDataLoader()
                result = data_loader.load_latest_momentum_data()
        
        assert result is None
    
    def test_load_momentum_data_by_date_success(self, data_loader):
        """Test loading data for specific date."""
        with patch('streamlit.cache_data', lambda **kwargs: lambda func: func):
            result = data_loader.load_momentum_data_by_date('2026-02-21')
        
        assert result is not None
        assert result['market_date'] == '2026-02-21'
    
    def test_get_available_dates(self, data_loader):
        """Test getting available dates."""
        with patch('streamlit.cache_data', lambda **kwargs: lambda func: func):
            dates = data_loader.get_available_dates()
        
        assert len(dates) == 2
        assert '2026-02-21' in dates
        assert '2026-02-20' in dates
    
    def test_transform_data_for_ui(self, data_loader):
        """Test data transformation for UI display."""
        raw_data = self._get_sample_data()
        transformed = data_loader.transform_data_for_ui(raw_data)
        
        assert 'metadata' in transformed
        assert 'tiers' in transformed
        assert 'summary' in transformed
        
        # Check tier transformation
        tier_data = transformed['tiers']['100B_200B']
        assert 'timeframes' in tier_data
        assert 'stats' in tier_data
        assert '7d' in tier_data['timeframes']
        
        # Check stock transformation
        stock = tier_data['timeframes']['7d'][0]
        assert stock['ticker'] == 'AAPL'
        assert abs(stock['momentum_pct'] - 5.23) < 0.01  # Allow for floating point precision
        assert stock['momentum_display'] == '+5.23%'
        assert stock['has_summary'] is True
    
    def test_format_market_cap(self, data_loader):
        """Test market cap formatting."""
        assert data_loader._format_market_cap(2400000000000) == '$2.4T'
        assert data_loader._format_market_cap(150000000000) == '$150.0B'
        assert data_loader._format_market_cap(5000000000) == '$5.0B'  # 5B, not 5000M
    
    def test_calculate_tier_stats(self, data_loader):
        """Test tier statistics calculation."""
        stocks = [
            {'momentum_value': 0.05, 'has_summary': True},
            {'momentum_value': 0.03, 'has_summary': False},
            {'momentum_value': 0.07, 'has_summary': True}
        ]
        
        stats = data_loader._calculate_tier_stats(stocks)
        
        assert stats['count'] == 3
        assert abs(stats['avg_momentum'] - 0.05) < 0.001  # Allow for floating point precision
        assert stats['max_momentum'] == 0.07
        assert stats['min_momentum'] == 0.03
        assert stats['stocks_with_summaries'] == 2
    
    def test_validate_data_freshness_fresh(self, data_loader):
        """Test data freshness validation for fresh data."""
        fresh_data = {
            'generated_at': datetime.now().isoformat() + 'Z'
        }
        
        assert data_loader.validate_data_freshness(fresh_data) is True
    
    def test_validate_data_freshness_stale(self, data_loader):
        """Test data freshness validation for stale data."""
        stale_time = datetime.now() - timedelta(hours=50)
        stale_data = {
            'generated_at': stale_time.isoformat() + 'Z'
        }
        
        assert data_loader.validate_data_freshness(stale_data) is False
    
    def test_handle_data_loading_error(self, data_loader):
        """Test error handling for data loading."""
        error = Exception("Test error")
        error_info = data_loader.handle_data_loading_error(error)
        
        assert error_info['error'] is True
        assert error_info['error_type'] == 'Exception'
        assert error_info['error_message'] == 'Test error'
        assert 'suggestions' in error_info
    
    def test_get_tier_display_name(self, data_loader):
        """Test tier display name conversion."""
        assert data_loader.get_tier_display_name('100B_200B') == '$100B - $200B'
        assert data_loader.get_tier_display_name('1T_plus') == '$1T+'
        assert data_loader.get_tier_display_name('unknown') == 'unknown'
    
    def test_get_timeframe_display_name(self, data_loader):
        """Test timeframe display name conversion."""
        assert data_loader.get_timeframe_display_name('7d') == '7 Days'
        assert data_loader.get_timeframe_display_name('30d') == '30 Days'
        assert data_loader.get_timeframe_display_name('unknown') == 'unknown'


class TestCacheManager:
    """Test cases for CacheManager."""
    
    @pytest.fixture
    def cache_manager(self):
        """Create cache manager with temporary directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield CacheManager(cache_dir=temp_dir)
    
    def test_set_and_get_memory_cache(self, cache_manager):
        """Test setting and getting from memory cache."""
        cache_manager.set('test_key', 'test_value', ttl=60, persist=False)
        
        result = cache_manager.get('test_key')
        assert result == 'test_value'
    
    def test_set_and_get_persistent_cache(self, cache_manager):
        """Test setting and getting from persistent cache."""
        cache_manager.set('test_key', 'test_value', ttl=60, persist=True)
        
        # Clear memory cache to force persistent cache read
        cache_manager._memory_cache.clear()
        cache_manager._cache_metadata.clear()
        
        result = cache_manager.get('test_key')
        assert result == 'test_value'
    
    def test_cache_expiration(self, cache_manager):
        """Test cache expiration."""
        cache_manager.set('test_key', 'test_value', ttl=0, persist=False)
        
        # Wait a moment for expiration
        import time
        time.sleep(0.1)
        
        result = cache_manager.get('test_key', default='default')
        assert result == 'default'
    
    def test_invalidate_cache(self, cache_manager):
        """Test cache invalidation."""
        cache_manager.set('test_key', 'test_value', ttl=60, persist=True)
        
        cache_manager.invalidate('test_key')
        
        result = cache_manager.get('test_key', default='default')
        assert result == 'default'
    
    def test_clear_all_cache(self, cache_manager):
        """Test clearing all cache entries."""
        cache_manager.set('key1', 'value1', ttl=60, persist=True)
        cache_manager.set('key2', 'value2', ttl=60, persist=True)
        
        cache_manager.clear_all()
        
        assert cache_manager.get('key1', default='default') == 'default'
        assert cache_manager.get('key2', default='default') == 'default'
    
    def test_cleanup_expired(self, cache_manager):
        """Test cleanup of expired entries."""
        cache_manager.set('expired_key', 'value', ttl=0, persist=True)
        cache_manager.set('valid_key', 'value', ttl=60, persist=True)
        
        import time
        time.sleep(0.1)
        
        cleaned_count = cache_manager.cleanup_expired()
        
        assert cleaned_count >= 1
        assert cache_manager.get('expired_key', default='default') == 'default'
        assert cache_manager.get('valid_key') == 'value'
    
    def test_get_cache_stats(self, cache_manager):
        """Test cache statistics."""
        cache_manager.set('key1', 'value1', ttl=60, persist=True)
        cache_manager.set('key2', 'value2', ttl=60, persist=False)
        
        stats = cache_manager.get_cache_stats()
        
        assert 'memory_entries' in stats
        assert 'persistent_entries' in stats
        assert 'total_size_bytes' in stats
        assert stats['memory_entries'] >= 2


class TestCachedDataLoader:
    """Test cases for CachedDataLoader."""
    
    @pytest.fixture
    def cached_loader(self):
        """Create cached data loader with temporary cache."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = CacheManager(cache_dir=temp_dir)
            yield CachedDataLoader(cache_manager)
    
    def test_cached_load_fresh_data(self, cached_loader):
        """Test loading fresh data with caching."""
        def mock_loader():
            return {'data': 'fresh_value'}
        
        result = cached_loader.cached_load('test_key', mock_loader, ttl=60)
        
        assert result == {'data': 'fresh_value'}
        
        # Second call should return cached data
        def mock_loader_2():
            return {'data': 'different_value'}
        
        result2 = cached_loader.cached_load('test_key', mock_loader_2, ttl=60)
        assert result2 == {'data': 'fresh_value'}  # Should be cached value
    
    def test_cached_load_with_exception(self, cached_loader):
        """Test cached load when loader function raises exception."""
        def failing_loader():
            raise Exception("Load failed")
        
        with pytest.raises(Exception, match="Load failed"):
            cached_loader.cached_load('test_key', failing_loader, ttl=60)
    
    def test_invalidate_pattern(self, cached_loader):
        """Test pattern-based cache invalidation."""
        cached_loader.cache_manager.set('pattern_key_1', 'value1', ttl=60)
        cached_loader.cache_manager.set('pattern_key_2', 'value2', ttl=60)
        cached_loader.cache_manager.set('other_key', 'value3', ttl=60)
        
        invalidated_count = cached_loader.invalidate_pattern('pattern_key')
        
        assert invalidated_count == 2
        assert cached_loader.cache_manager.get('pattern_key_1', 'default') == 'default'
        assert cached_loader.cache_manager.get('pattern_key_2', 'default') == 'default'
        assert cached_loader.cache_manager.get('other_key') == 'value3'


class TestDataTransformer:
    """Test cases for DataTransformer."""
    
    @pytest.fixture
    def transformer(self):
        """Create data transformer instance."""
        return DataTransformer()
    
    @pytest.fixture
    def sample_stocks(self):
        """Sample stock data for testing."""
        return [
            {
                'ticker': 'AAPL',
                'company_name': 'Apple Inc.',
                'price_display': '$150.25',
                'market_cap_display': '$2.4T',
                'momentum_display': '+5.23%',
                'has_summary': True,
                'momentum_value': 0.0523,
                'momentum_pct': 5.23,  # Add momentum_pct field
                'current_price': 150.25,
                'market_cap': 2400000000000
            },
            {
                'ticker': 'MSFT',
                'company_name': 'Microsoft Corporation',
                'price_display': '$280.50',
                'market_cap_display': '$2.1T',
                'momentum_display': '+3.45%',
                'has_summary': False,
                'momentum_value': 0.0345,
                'momentum_pct': 3.45,  # Add momentum_pct field
                'current_price': 280.50,
                'market_cap': 2100000000000
            }
        ]
    
    def test_create_stock_dataframe(self, transformer, sample_stocks):
        """Test creating stock DataFrame."""
        df = transformer.create_stock_dataframe(sample_stocks, '7d')
        
        assert not df.empty
        assert len(df) == 2
        assert 'Ticker' in df.columns
        assert 'Company' in df.columns
        assert 'Momentum' in df.columns
        assert df.iloc[0]['Ticker'] == 'AAPL'
    
    def test_create_stock_dataframe_empty(self, transformer):
        """Test creating DataFrame with empty stock list."""
        df = transformer.create_stock_dataframe([], '7d')
        assert df.empty
    
    def test_filter_stocks_by_criteria(self, transformer, sample_stocks):
        """Test filtering stocks by various criteria."""
        # Filter by momentum
        filtered = transformer.filter_stocks_by_criteria(
            sample_stocks, min_momentum=0.04
        )
        assert len(filtered) == 1
        assert filtered[0]['ticker'] == 'AAPL'
        
        # Filter by AI summary
        filtered = transformer.filter_stocks_by_criteria(
            sample_stocks, has_summary=True
        )
        assert len(filtered) == 1
        assert filtered[0]['ticker'] == 'AAPL'
        
        # Filter by market cap
        filtered = transformer.filter_stocks_by_criteria(
            sample_stocks, min_market_cap=2200000000000
        )
        assert len(filtered) == 1
        assert filtered[0]['ticker'] == 'AAPL'
    
    def test_sort_stocks(self, transformer, sample_stocks):
        """Test sorting stocks by different criteria."""
        # Sort by momentum (descending)
        sorted_stocks = transformer.sort_stocks(sample_stocks, 'momentum', ascending=False)
        assert sorted_stocks[0]['ticker'] == 'AAPL'
        assert sorted_stocks[1]['ticker'] == 'MSFT'
        
        # Sort by ticker (ascending)
        sorted_stocks = transformer.sort_stocks(sample_stocks, 'ticker', ascending=True)
        assert sorted_stocks[0]['ticker'] == 'AAPL'
        assert sorted_stocks[1]['ticker'] == 'MSFT'
    
    def test_calculate_momentum_distribution(self, transformer, sample_stocks):
        """Test momentum distribution calculation."""
        distribution = transformer.calculate_momentum_distribution(sample_stocks)
        
        assert distribution['count'] == 2
        assert distribution['mean'] == (0.0523 + 0.0345) / 2
        assert distribution['max'] == 0.0523
        assert distribution['min'] == 0.0345
        assert distribution['positive_count'] == 2
        assert distribution['negative_count'] == 0
    
    def test_format_data_for_export(self, transformer, sample_stocks):
        """Test formatting data for export."""
        export_data = transformer.format_data_for_export(
            sample_stocks, '$100B - $200B', '7d'
        )
        
        assert 'metadata' in export_data
        assert 'stocks' in export_data
        assert export_data['metadata']['tier'] == '$100B - $200B'
        assert export_data['metadata']['timeframe'] == '7d'
        assert len(export_data['stocks']) == 2
        
        stock = export_data['stocks'][0]
        assert stock['rank'] == 1
        assert stock['ticker'] == 'AAPL'
        assert abs(stock['momentum_percentage'] - 5.23) < 0.01  # Allow for floating point precision


if __name__ == '__main__':
    pytest.main([__file__])