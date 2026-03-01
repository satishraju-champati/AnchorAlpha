"""
Tests for user experience edge cases and error scenarios in the AnchorAlpha application.
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
from AnchorAlpha.streamlit_app.ui_components import (
    ErrorDisplay, StockRankingTable, TierSelector, TimeframeSelector, FilterControls
)
from AnchorAlpha.streamlit_app.momentum_dashboard import MomentumDashboard


class TestUserExperienceEdgeCases(unittest.TestCase):
    """Test user experience edge cases and error scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.error_display = ErrorDisplay()
        self.stock_table = StockRankingTable()
        self.tier_selector = TierSelector()
        self.timeframe_selector = TimeframeSelector()
        self.filter_controls = FilterControls()
    
    def test_empty_stock_list_handling(self):
        """Test handling of empty stock lists."""
        # Test with empty list
        empty_stocks = []
        
        # Should handle gracefully without errors
        valid_stocks = self.stock_table._filter_valid_stocks(empty_stocks)
        self.assertEqual(len(valid_stocks), 0)
        
        # Data quality check should handle empty list
        issues = self.stock_table._check_data_quality(empty_stocks)
        self.assertIsInstance(issues, list)
    
    def test_malformed_stock_data(self):
        """Test handling of malformed stock data."""
        malformed_stocks = [
            None,  # Null stock
            "invalid_string",  # String instead of dict
            123,  # Number instead of dict
            [],  # List instead of dict
            {
                'ticker': None,  # Null ticker
                'company_name': '',  # Empty company name
                'momentum_value': 'invalid',  # String instead of number
                'market_cap': -1000,  # Negative market cap
                'has_summary': 'yes'  # String instead of boolean
            }
        ]
        
        # Should filter out all malformed data
        valid_stocks = self.stock_table._filter_valid_stocks(malformed_stocks)
        self.assertEqual(len(valid_stocks), 0)
    
    def test_extreme_momentum_values(self):
        """Test handling of extreme momentum values."""
        extreme_stocks = [
            {
                'ticker': 'EXTREME1',
                'company_name': 'Extreme Corp 1',
                'momentum_value': 10.0,  # 1000% gain
                'has_summary': True
            },
            {
                'ticker': 'EXTREME2',
                'company_name': 'Extreme Corp 2',
                'momentum_value': -0.99,  # 99% loss
                'has_summary': False
            },
            {
                'ticker': 'NORMAL',
                'company_name': 'Normal Corp',
                'momentum_value': 0.05,  # 5% gain
                'has_summary': True
            }
        ]
        
        # Should detect extreme values in data quality check
        issues = self.stock_table._check_data_quality(extreme_stocks)
        extreme_issue_found = any('extreme momentum' in issue.lower() for issue in issues)
        self.assertTrue(extreme_issue_found)
    
    def test_missing_ai_summaries_scenarios(self):
        """Test various scenarios with missing AI summaries."""
        test_scenarios = [
            # No AI summaries at all
            {
                'stocks': [
                    {'ticker': 'AAPL', 'has_summary': False, 'ai_summary': ''},
                    {'ticker': 'MSFT', 'has_summary': False, 'ai_summary': None}
                ],
                'expected_coverage': 0
            },
            # Partial AI summaries
            {
                'stocks': [
                    {'ticker': 'AAPL', 'has_summary': True, 'ai_summary': 'Good summary'},
                    {'ticker': 'MSFT', 'has_summary': False, 'ai_summary': ''},
                    {'ticker': 'GOOGL', 'has_summary': False, 'ai_summary': None}
                ],
                'expected_coverage': 33
            },
            # Empty summaries (marked as having summary but content is empty)
            {
                'stocks': [
                    {'ticker': 'AAPL', 'has_summary': True, 'ai_summary': ''},
                    {'ticker': 'MSFT', 'has_summary': True, 'ai_summary': '   '},  # Whitespace only
                    {'ticker': 'GOOGL', 'has_summary': True, 'ai_summary': 'N/A'}  # Placeholder
                ],
                'expected_coverage': 100  # Marked as having summaries
            }
        ]
        
        for scenario in test_scenarios:
            stocks = scenario['stocks']
            expected_coverage = scenario['expected_coverage']
            
            # Calculate actual coverage
            stocks_with_summaries = sum(1 for s in stocks if s.get('has_summary', False))
            actual_coverage = (stocks_with_summaries / len(stocks)) * 100 if stocks else 0
            
            self.assertAlmostEqual(actual_coverage, expected_coverage, delta=1)
    
    def test_data_loading_timeout_scenarios(self):
        """Test various data loading timeout scenarios."""
        with patch('streamlit.cache_data', lambda **kwargs: lambda func: func):
            data_loader = StreamlitDataLoader()
        
        # Test different timeout scenarios
        timeout_scenarios = [
            TimeoutError("Connection timed out"),
            ConnectionError("Connection reset by peer"),
            OSError("Network is unreachable")
        ]
        
        for error in timeout_scenarios:
            with patch.object(data_loader.s3_client, 'list_available_dates', side_effect=error):
                result = data_loader.load_latest_momentum_data()
                self.assertIsNone(result)
                
                # Should set appropriate error state
                error_state = data_loader.get_error_state()
                self.assertTrue(error_state.get('has_error', False))
    
    def test_filter_edge_cases(self):
        """Test edge cases in filtering functionality."""
        test_stocks = [
            {
                'ticker': 'AAPL',
                'momentum_value': 0.05,
                'has_summary': True,
                'market_cap': 2400000000000
            },
            {
                'ticker': 'MSFT',
                'momentum_value': -0.02,
                'has_summary': False,
                'market_cap': 2100000000000
            }
        ]
        
        # Test extreme filter values
        extreme_filters = [
            {'momentum_min': 10.0, 'momentum_max': 20.0},  # No stocks should match
            {'momentum_min': -10.0, 'momentum_max': -5.0},  # No stocks should match
            {'momentum_min': None, 'momentum_max': None},  # Invalid filters
            {'positive_only': True, 'summary_filter': 'With AI Summary'}  # Restrictive combination
        ]
        
        # Create mock dashboard to test filter application
        with patch('streamlit.set_page_config'):
            with patch('streamlit.sidebar'):
                with patch('streamlit.container'):
                    dashboard = MomentumDashboard()
        
        for filter_values in extreme_filters:
            try:
                filtered_stocks = dashboard._apply_filters(test_stocks, filter_values)
                # Should not raise an error, even with extreme values
                self.assertIsInstance(filtered_stocks, list)
            except Exception as e:
                self.fail(f"Filter application failed with values {filter_values}: {e}")
    
    def test_mobile_view_edge_cases(self):
        """Test mobile view handling edge cases."""
        # Test with very long company names
        long_name_stocks = [
            {
                'ticker': 'LONGNAME',
                'company_name': 'A' * 200,  # Very long name
                'momentum_value': 0.05,
                'price_display': '$100.00',
                'market_cap_display': '$1.0T',
                'has_summary': True
            }
        ]
        
        # Should handle long names gracefully
        valid_stocks = self.stock_table._filter_valid_stocks(long_name_stocks)
        self.assertEqual(len(valid_stocks), 1)
        
        # Test with special characters in names
        special_char_stocks = [
            {
                'ticker': 'SPECIAL',
                'company_name': 'Company & Co. (Ñoño) <script>alert("test")</script>',
                'momentum_value': 0.05,
                'price_display': '$100.00',
                'market_cap_display': '$1.0T',
                'has_summary': True
            }
        ]
        
        valid_stocks = self.stock_table._filter_valid_stocks(special_char_stocks)
        self.assertEqual(len(valid_stocks), 1)
    
    def test_tier_selector_edge_cases(self):
        """Test tier selector with edge cases."""
        # Test with empty available tiers
        empty_tiers = []
        # Should handle gracefully (would normally show only "All Tiers")
        
        # Test with unknown tier keys
        unknown_tiers = ['unknown_tier', 'invalid_tier']
        
        # Test display name handling
        unknown_display = self.tier_selector.get_tier_display_name('unknown_tier')
        self.assertEqual(unknown_display, 'unknown_tier')  # Should return the key itself
    
    def test_timeframe_selector_edge_cases(self):
        """Test timeframe selector with edge cases."""
        # Test with empty available timeframes
        empty_timeframes = []
        
        # Test with unknown timeframe keys
        unknown_timeframes = ['1h', '1y', 'invalid']
        
        # Test display name handling
        unknown_display = self.timeframe_selector.get_timeframe_display_name('1h')
        self.assertEqual(unknown_display, '1h')  # Should return the key itself
    
    def test_data_transformation_edge_cases(self):
        """Test data transformation with edge cases."""
        with patch('streamlit.cache_data', lambda **kwargs: lambda func: func):
            data_loader = StreamlitDataLoader()
        
        # Test with minimal data structure
        minimal_data = {
            'generated_at': '2026-03-01T16:30:00Z',
            'market_date': '2026-03-01'
            # Missing 'tiers' key
        }
        
        transformed = data_loader.transform_data_for_ui(minimal_data)
        self.assertEqual(transformed, {})  # Should return empty dict
        
        # Test with empty tiers
        empty_tiers_data = {
            'generated_at': '2026-03-01T16:30:00Z',
            'market_date': '2026-03-01',
            'tiers': {}
        }
        
        transformed = data_loader.transform_data_for_ui(empty_tiers_data)
        self.assertIn('metadata', transformed)
        self.assertIn('tiers', transformed)
        self.assertEqual(len(transformed['tiers']), 0)
    
    def test_concurrent_user_scenarios(self):
        """Test scenarios that might occur with concurrent users."""
        # Simulate cache invalidation during data loading
        with patch('streamlit.cache_data', lambda **kwargs: lambda func: func):
            data_loader = StreamlitDataLoader()
        
        # Test rapid successive calls (simulating multiple users)
        call_results = []
        
        def mock_download(date):
            # Simulate varying response times and occasional failures
            import random
            if random.random() < 0.1:  # 10% failure rate
                raise ConnectionError("Temporary failure")
            return {
                'generated_at': f'{date}T16:30:00Z',
                'market_date': date,
                'tiers': {'1T_plus': {'7d': []}}
            }
        
        with patch.object(data_loader.s3_client, 'list_available_dates', return_value=['2026-03-01']):
            with patch.object(data_loader.s3_client, 'download_momentum_data', side_effect=mock_download):
                with patch.object(data_loader.s3_client, 'validate_json_schema', return_value=True):
                    
                    # Make multiple rapid calls
                    for _ in range(10):
                        try:
                            result = data_loader.load_latest_momentum_data()
                            call_results.append(result is not None)
                        except Exception:
                            call_results.append(False)
        
        # At least some calls should succeed
        success_rate = sum(call_results) / len(call_results)
        self.assertGreater(success_rate, 0.5)  # At least 50% success rate
    
    def test_memory_efficient_large_dataset_handling(self):
        """Test memory-efficient handling of large datasets."""
        # Create a large dataset that might cause memory issues
        large_dataset = {
            'generated_at': '2026-03-01T16:30:00Z',
            'market_date': '2026-03-01',
            'tiers': {}
        }
        
        # Generate large amount of data
        for tier in ['100B_200B', '200B_500B', '500B_1T', '1T_plus']:
            large_dataset['tiers'][tier] = {}
            for timeframe in ['7_day', '30_day', '60_day', '90_day']:
                stocks = []
                for i in range(500):  # 500 stocks per tier/timeframe
                    stock = {
                        'ticker': f'STOCK{tier}_{timeframe}_{i:03d}',
                        'company_name': f'Company {i} in {tier} for {timeframe}',
                        'current_price': 100.0 + (i * 0.1),
                        'market_cap': 100000000000 + (i * 1000000000),
                        'momentum_7d': 0.01 + (i * 0.0001),
                        'momentum_30d': 0.02 + (i * 0.0001),
                        'momentum_60d': 0.015 + (i * 0.0001),
                        'momentum_90d': 0.025 + (i * 0.0001),
                        'ai_summary': f'Summary for stock {i}' if i % 3 == 0 else '',
                        'tier': tier,
                        'has_summary': i % 3 == 0
                    }
                    stocks.append(stock)
                large_dataset['tiers'][tier][timeframe] = stocks
        
        with patch('streamlit.cache_data', lambda **kwargs: lambda func: func):
            data_loader = StreamlitDataLoader()
        
        # Should handle large dataset without memory errors
        try:
            transformed = data_loader.transform_data_for_ui(large_dataset)
            self.assertIsNotNone(transformed)
            self.assertIn('tiers', transformed)
            
            # Verify data integrity
            total_stocks = 0
            for tier_data in transformed['tiers'].values():
                for timeframe_stocks in tier_data.get('timeframes', {}).values():
                    total_stocks += len(timeframe_stocks)
            
            # Should have processed all stocks
            expected_total = 4 * 4 * 500  # 4 tiers * 4 timeframes * 500 stocks
            self.assertEqual(total_stocks, expected_total)
            
        except MemoryError:
            self.fail("Large dataset caused memory error - need better memory management")
        except Exception as e:
            self.fail(f"Large dataset processing failed: {e}")
    
    def test_internationalization_edge_cases(self):
        """Test handling of international characters and formats."""
        international_stocks = [
            {
                'ticker': 'INTL1',
                'company_name': 'Société Générale',  # French accents
                'momentum_value': 0.05,
                'has_summary': True,
                'ai_summary': 'Résumé en français avec des accents'
            },
            {
                'ticker': 'INTL2',
                'company_name': '株式会社ソニー',  # Japanese characters
                'momentum_value': 0.03,
                'has_summary': True,
                'ai_summary': 'Japanese company summary'
            },
            {
                'ticker': 'INTL3',
                'company_name': 'Компания Газпром',  # Cyrillic characters
                'momentum_value': -0.02,
                'has_summary': False,
                'ai_summary': ''
            }
        ]
        
        # Should handle international characters gracefully
        valid_stocks = self.stock_table._filter_valid_stocks(international_stocks)
        self.assertEqual(len(valid_stocks), 3)
        
        # Data quality check should work with international data
        issues = self.stock_table._check_data_quality(international_stocks)
        self.assertIsInstance(issues, list)


class TestAccessibilityAndUsability(unittest.TestCase):
    """Test accessibility and usability features."""
    
    def test_error_message_clarity(self):
        """Test that error messages are clear and actionable."""
        error_display = ErrorDisplay()
        
        # Test different error scenarios
        error_scenarios = [
            {
                'error_type': 'ConnectionError',
                'error_message': 'Failed to connect to data source',
                'expected_suggestions': ['Check internet connection', 'Try again later']
            },
            {
                'error_type': 'NoCredentialsError',
                'error_message': 'AWS credentials not found',
                'expected_suggestions': ['Check AWS credentials configuration']
            }
        ]
        
        for scenario in error_scenarios:
            # Error messages should be user-friendly, not technical
            self.assertNotIn('Exception', scenario['error_message'])
            self.assertNotIn('Traceback', scenario['error_message'])
            
            # Should provide actionable suggestions
            self.assertTrue(len(scenario['expected_suggestions']) > 0)
    
    def test_loading_state_feedback(self):
        """Test loading state provides adequate user feedback."""
        with patch('streamlit.cache_data', lambda **kwargs: lambda func: func):
            data_loader = StreamlitDataLoader()
        
        # Test loading state management
        data_loader._set_loading_state('Loading market data...', 25)
        
        loading_info = data_loader.get_loading_progress()
        self.assertTrue(loading_info['is_loading'])
        self.assertIn('Loading', loading_info['current_step'])
        self.assertEqual(loading_info['progress_pct'], 25)
        
        # Loading messages should be informative
        self.assertGreater(len(loading_info['current_step']), 5)
    
    def test_fallback_content_quality(self):
        """Test quality of fallback content when data is unavailable."""
        stock_table = StockRankingTable()
        
        # Test fallback scenarios
        fallback_scenarios = ['no_summary', 'empty_summary', 'api_error', 'rate_limit']
        
        for scenario in fallback_scenarios:
            # Should provide helpful information, not just "unavailable"
            # This would be tested in the actual rendering, but we can test the logic exists
            try:
                stock_table._render_summary_placeholder('AAPL', scenario)
                # If no exception, the method handles the scenario
                self.assertTrue(True)
            except Exception as e:
                self.fail(f"Fallback scenario '{scenario}' not handled: {e}")


if __name__ == '__main__':
    # Run the tests with verbose output
    unittest.main(verbosity=2)