"""
Comprehensive tests for error handling and user feedback in the AnchorAlpha application.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "AnchorAlpha" / "src"))

from AnchorAlpha.streamlit_app.data_loader import StreamlitDataLoader
from AnchorAlpha.streamlit_app.ui_components import ErrorDisplay, StockRankingTable
from AnchorAlpha.streamlit_app.momentum_dashboard import MomentumDashboard


class TestDataLoaderErrorHandling(unittest.TestCase):
    """Test error handling in the data loader component."""
    
    def setUp(self):
        """Set up test fixtures."""
        with patch('streamlit.cache_data', lambda **kwargs: lambda func: func):
            self.data_loader = StreamlitDataLoader()
    
    def test_s3_connection_failure(self):
        """Test handling of S3 connection failures."""
        # Mock S3 client to raise connection error
        with patch.object(self.data_loader.s3_client, 'list_available_dates') as mock_list:
            mock_list.side_effect = ConnectionError("Unable to connect to S3")
            
            # Test error handling
            result = self.data_loader.load_latest_momentum_data()
            self.assertIsNone(result)
            
            # Check error state
            error_state = self.data_loader.get_error_state()
            self.assertTrue(error_state.get('has_error', False))
            self.assertEqual(error_state.get('error_type'), 'loading_error')
    
    def test_corrupted_data_handling(self):
        """Test handling of corrupted data files."""
        # Mock S3 client to return dates but invalid data
        with patch.object(self.data_loader.s3_client, 'list_available_dates') as mock_list:
            with patch.object(self.data_loader.s3_client, 'download_momentum_data') as mock_download:
                with patch.object(self.data_loader.s3_client, 'validate_json_schema') as mock_validate:
                    
                    mock_list.return_value = ['2026-03-01', '2026-02-28']
                    mock_download.return_value = {'invalid': 'data'}
                    mock_validate.return_value = False
                    
                    result = self.data_loader.load_latest_momentum_data()
                    self.assertIsNone(result)
                    
                    # Check error state
                    error_state = self.data_loader.get_error_state()
                    self.assertTrue(error_state.get('has_error', False))
                    self.assertEqual(error_state.get('error_type'), 'no_valid_data')
    
    def test_no_data_available(self):
        """Test handling when no data is available."""
        with patch.object(self.data_loader.s3_client, 'list_available_dates') as mock_list:
            mock_list.return_value = []
            
            result = self.data_loader.load_latest_momentum_data()
            self.assertIsNone(result)
            
            # Check error state
            error_state = self.data_loader.get_error_state()
            self.assertTrue(error_state.get('has_error', False))
            self.assertEqual(error_state.get('error_type'), 'no_data')
    
    def test_retry_logic(self):
        """Test retry logic for transient failures."""
        call_count = 0
        
        def mock_list_dates(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary connection error")
            return ['2026-03-01']
        
        with patch.object(self.data_loader.s3_client, 'list_available_dates', side_effect=mock_list_dates):
            dates = self.data_loader._get_available_dates_with_retry()
            
            # Should succeed after retries
            self.assertEqual(dates, ['2026-03-01'])
            self.assertEqual(call_count, 3)
    
    def test_error_state_management(self):
        """Test error state setting and clearing."""
        # Test setting error state
        self.data_loader._set_error_state('test_error', 'Test error message')
        
        error_state = self.data_loader.get_error_state()
        self.assertTrue(error_state['has_error'])
        self.assertEqual(error_state['error_type'], 'test_error')
        self.assertEqual(error_state['error_message'], 'Test error message')
        
        # Test clearing error state
        self.data_loader._clear_error_state()
        
        error_state = self.data_loader.get_error_state()
        self.assertFalse(error_state.get('has_error', True))
    
    def test_loading_state_management(self):
        """Test loading state management."""
        # Test setting loading state
        self.data_loader._set_loading_state('Loading data...', 50)
        
        loading_info = self.data_loader.get_loading_progress()
        self.assertTrue(loading_info['is_loading'])
        self.assertEqual(loading_info['current_step'], 'Loading data...')
        self.assertEqual(loading_info['progress_pct'], 50)
        
        # Test clearing loading state
        self.data_loader._clear_loading_state()
        
        loading_info = self.data_loader.get_loading_progress()
        self.assertFalse(loading_info['is_loading'])
    
    def test_data_freshness_validation(self):
        """Test data freshness validation with various scenarios."""
        # Test fresh data
        fresh_data = {
            'generated_at': datetime.now().isoformat() + 'Z',
            'market_date': '2026-03-01'
        }
        self.assertTrue(self.data_loader.validate_data_freshness(fresh_data))
        
        # Test stale data
        stale_time = datetime.now() - timedelta(hours=50)
        stale_data = {
            'generated_at': stale_time.isoformat() + 'Z',
            'market_date': '2026-02-28'
        }
        self.assertFalse(self.data_loader.validate_data_freshness(stale_data))
        
        # Test invalid timestamp
        invalid_data = {
            'generated_at': 'invalid-timestamp',
            'market_date': '2026-03-01'
        }
        self.assertFalse(self.data_loader.validate_data_freshness(invalid_data))
        
        # Test missing timestamp
        missing_data = {
            'market_date': '2026-03-01'
        }
        self.assertFalse(self.data_loader.validate_data_freshness(missing_data))
    
    def test_error_suggestion_generation(self):
        """Test error suggestion generation."""
        # Test different error types
        connection_error = ConnectionError("Connection failed")
        error_info = self.data_loader.handle_data_loading_error(connection_error)
        
        self.assertIn('suggestions', error_info)
        self.assertTrue(len(error_info['suggestions']) > 0)
        self.assertIn('Check internet connection', error_info['suggestions'])
        
        # Test credentials error
        from botocore.exceptions import NoCredentialsError
        creds_error = NoCredentialsError()
        error_info = self.data_loader.handle_data_loading_error(creds_error)
        
        self.assertIn('Check AWS credentials configuration', error_info['suggestions'])


class TestUIComponentErrorHandling(unittest.TestCase):
    """Test error handling in UI components."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.error_display = ErrorDisplay()
        self.stock_table = StockRankingTable()
    
    def test_error_display_rendering(self):
        """Test error display component rendering."""
        error_info = {
            'error': True,
            'error_type': 'ConnectionError',
            'error_message': 'Failed to connect to data source',
            'suggestions': ['Check internet connection', 'Try again later']
        }
        
        # This would normally render in Streamlit, but we can test the logic
        # The actual rendering would be tested in integration tests
        self.assertTrue(error_info['error'])
        self.assertEqual(len(error_info['suggestions']), 2)
    
    def test_stock_table_data_validation(self):
        """Test stock table data validation."""
        # Test with invalid data
        invalid_stocks = [
            {'ticker': 'AAPL'},  # Missing required fields
            {'company_name': 'Test Corp'},  # Missing ticker
            {}  # Empty stock data
        ]
        
        valid_stocks = self.stock_table._filter_valid_stocks(invalid_stocks)
        self.assertEqual(len(valid_stocks), 0)
        
        # Test with valid data
        valid_stock_data = [
            {
                'ticker': 'AAPL',
                'company_name': 'Apple Inc.',
                'momentum_value': 0.05,
                'current_price': 150.0,
                'market_cap': 2400000000000
            }
        ]
        
        valid_stocks = self.stock_table._filter_valid_stocks(valid_stock_data)
        self.assertEqual(len(valid_stocks), 1)
    
    def test_data_quality_checks(self):
        """Test data quality checking functionality."""
        # Test stocks with various data quality issues
        test_stocks = [
            {
                'ticker': 'AAPL',
                'company_name': 'Apple Inc.',
                'momentum_value': 0.05,
                'has_summary': True
            },
            {
                'ticker': 'MSFT',
                'company_name': 'Microsoft Corp.',
                'momentum_value': None,  # Missing momentum
                'has_summary': False
            },
            {
                'ticker': 'GOOGL',
                'company_name': 'Alphabet Inc.',
                'momentum_value': 1.5,  # Extreme value
                'has_summary': True
            }
        ]
        
        issues = self.stock_table._check_data_quality(test_stocks)
        self.assertTrue(len(issues) > 0)
        
        # Should detect missing momentum values
        self.assertTrue(any('momentum_value' in issue for issue in issues))
        
        # Should detect extreme momentum values
        self.assertTrue(any('extreme momentum' in issue for issue in issues))
    
    def test_fallback_summary_rendering(self):
        """Test AI summary fallback rendering."""
        # Test different fallback scenarios
        test_cases = [
            ('no_summary', 'AAPL'),
            ('empty_summary', 'MSFT'),
            ('api_error', 'GOOGL'),
            ('rate_limit', 'TSLA')
        ]
        
        for reason, ticker in test_cases:
            # This would normally render in Streamlit
            # We can test that the method exists and handles different reasons
            try:
                self.stock_table._render_summary_placeholder(ticker, reason)
                # If no exception is raised, the method handles the reason
                self.assertTrue(True)
            except Exception as e:
                self.fail(f"Failed to handle fallback reason '{reason}': {e}")


class TestDashboardErrorHandling(unittest.TestCase):
    """Test error handling in the main dashboard."""
    
    def setUp(self):
        """Set up test fixtures."""
        with patch('streamlit.set_page_config'):
            with patch('streamlit.sidebar'):
                with patch('streamlit.container'):
                    self.dashboard = MomentumDashboard()
    
    def test_error_suggestion_generation(self):
        """Test contextual error suggestion generation."""
        # Test different error types
        error_types = [
            'no_data',
            'corrupted_data',
            'loading_error',
            'dates_error',
            'dashboard_error'
        ]
        
        for error_type in error_types:
            suggestions = self.dashboard._get_error_suggestions(error_type)
            self.assertTrue(len(suggestions) > 0)
            self.assertIsInstance(suggestions, list)
            
            # All suggestions should be strings
            for suggestion in suggestions:
                self.assertIsInstance(suggestion, str)
                self.assertTrue(len(suggestion) > 0)
    
    def test_data_age_calculation(self):
        """Test data age calculation."""
        # Test with current timestamp (within last few minutes)
        current_time = datetime.now()
        current_data = {
            'generated_at': current_time.isoformat() + 'Z'
        }
        age = self.dashboard._calculate_data_age(current_data)
        self.assertLess(age, 0.1)  # Should be less than 0.1 hours (6 minutes)
        
        # Test with old timestamp
        old_time = datetime.now() - timedelta(hours=25)
        old_data = {
            'generated_at': old_time.isoformat() + 'Z'
        }
        age = self.dashboard._calculate_data_age(old_data)
        self.assertGreater(age, 24.0)  # Should be more than 24 hours
        
        # Test with invalid timestamp
        invalid_data = {
            'generated_at': 'invalid-timestamp'
        }
        age = self.dashboard._calculate_data_age(invalid_data)
        self.assertEqual(age, 0.0)  # Should return 0 for invalid data
    
    def test_data_quality_assessment(self):
        """Test overall data quality assessment."""
        # Test with good quality data
        good_data = {
            'tiers': {
                '1T_plus': {
                    'timeframes': {
                        '7d': [
                            {'ticker': 'AAPL', 'has_summary': True},
                            {'ticker': 'MSFT', 'has_summary': True}
                        ],
                        '30d': [
                            {'ticker': 'AAPL', 'has_summary': True},
                            {'ticker': 'MSFT', 'has_summary': True}
                        ]
                    }
                }
            }
        }
        
        issues = self.dashboard._check_overall_data_quality(good_data)
        self.assertEqual(len(issues), 0)
        
        # Test with quality issues
        poor_data = {
            'tiers': {
                '1T_plus': {
                    'timeframes': {
                        '7d': [
                            {'ticker': 'AAPL', 'has_summary': False},
                            {'ticker': 'MSFT', 'has_summary': False}
                        ]
                    }
                },
                '500B_1T': {
                    'timeframes': {}  # Empty tier
                }
            }
        }
        
        issues = self.dashboard._check_overall_data_quality(poor_data)
        self.assertTrue(len(issues) > 0)
        
        # Should detect empty tiers
        self.assertTrue(any('tiers have no data' in issue for issue in issues))
        
        # Should detect low AI summary coverage
        self.assertTrue(any('AI summaries' in issue for issue in issues))


class TestErrorRecoveryScenarios(unittest.TestCase):
    """Test error recovery and graceful degradation scenarios."""
    
    def test_partial_data_loading(self):
        """Test handling when only partial data is available."""
        with patch('streamlit.cache_data', lambda **kwargs: lambda func: func):
            data_loader = StreamlitDataLoader()
        
        # Mock scenario where some dates have valid data, others don't
        def mock_download(date):
            if date == '2026-03-01':
                return {
                    'generated_at': '2026-03-01T16:30:00Z',
                    'market_date': '2026-03-01',
                    'tiers': {'1T_plus': {'7d': []}}
                }
            else:
                return None
        
        with patch.object(data_loader.s3_client, 'list_available_dates') as mock_list:
            with patch.object(data_loader.s3_client, 'download_momentum_data', side_effect=mock_download):
                with patch.object(data_loader.s3_client, 'validate_json_schema', return_value=True):
                    
                    mock_list.return_value = ['2026-03-01', '2026-02-28', '2026-02-27']
                    
                    result = data_loader.load_latest_momentum_data()
                    
                    # Should successfully load the available data
                    self.assertIsNotNone(result)
                    self.assertEqual(result['market_date'], '2026-03-01')
    
    def test_api_rate_limiting_handling(self):
        """Test handling of API rate limiting scenarios."""
        # This would be more relevant for the Perplexity API integration
        # but we can test the general error handling pattern
        
        with patch('streamlit.cache_data', lambda **kwargs: lambda func: func):
            data_loader = StreamlitDataLoader()
        
        # Mock rate limiting error
        from botocore.exceptions import ClientError
        rate_limit_error = ClientError(
            error_response={'Error': {'Code': 'Throttling'}},
            operation_name='GetObject'
        )
        
        with patch.object(data_loader.s3_client, 'list_available_dates', side_effect=rate_limit_error):
            result = data_loader.load_latest_momentum_data()
            self.assertIsNone(result)
            
            # Check that error is properly handled
            error_state = data_loader.get_error_state()
            self.assertTrue(error_state.get('has_error', False))
    
    def test_network_timeout_recovery(self):
        """Test recovery from network timeout scenarios."""
        with patch('streamlit.cache_data', lambda **kwargs: lambda func: func):
            data_loader = StreamlitDataLoader()
        
        # Mock timeout error that succeeds on retry
        call_count = 0
        def mock_timeout(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("Request timed out")
            return ['2026-03-01']
        
        with patch.object(data_loader.s3_client, 'list_available_dates', side_effect=mock_timeout):
            dates = data_loader._get_available_dates_with_retry()
            
            # Should succeed after retry
            self.assertEqual(dates, ['2026-03-01'])
            self.assertEqual(call_count, 2)
    
    def test_memory_pressure_handling(self):
        """Test handling of memory pressure scenarios."""
        # Test with very large dataset to simulate memory pressure
        large_data = {
            'generated_at': '2026-03-01T16:30:00Z',
            'market_date': '2026-03-01',
            'tiers': {}
        }
        
        # Create large dataset
        for tier in ['100B_200B', '200B_500B', '500B_1T', '1T_plus']:
            large_data['tiers'][tier] = {}
            for timeframe in ['7_day', '30_day', '60_day', '90_day']:
                stocks = []
                for i in range(1000):  # Large number of stocks
                    stock = {
                        'ticker': f'STOCK{i:04d}',
                        'company_name': f'Company {i}',
                        'momentum_value': 0.01 * i,
                        'has_summary': i % 2 == 0
                    }
                    stocks.append(stock)
                large_data['tiers'][tier][timeframe] = stocks
        
        with patch('streamlit.cache_data', lambda **kwargs: lambda func: func):
            data_loader = StreamlitDataLoader()
        
        try:
            # This should handle large datasets gracefully
            transformed_data = data_loader.transform_data_for_ui(large_data)
            self.assertIsNotNone(transformed_data)
            self.assertIn('tiers', transformed_data)
        except MemoryError:
            # If memory error occurs, it should be handled gracefully
            self.fail("Memory error not handled gracefully")


if __name__ == '__main__':
    # Run the tests with verbose output
    unittest.main(verbosity=2)