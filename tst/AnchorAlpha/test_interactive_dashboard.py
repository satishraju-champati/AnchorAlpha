"""
Comprehensive tests for the interactive dashboard and filtering system.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "AnchorAlpha" / "src"))

from AnchorAlpha.streamlit_app.momentum_dashboard import MomentumDashboard
from AnchorAlpha.streamlit_app.ui_components import (
    TierSelector, TimeframeSelector, StockRankingTable, FilterControls
)
from AnchorAlpha.streamlit_app.data_transforms import DataTransformer
from AnchorAlpha.streamlit_app.styling import AnchorAlphaTheme


class TestInteractiveDashboard(unittest.TestCase):
    """Test cases for interactive dashboard functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sample_stock_data = [
            {
                'ticker': 'AAPL',
                'company_name': 'Apple Inc.',
                'current_price': 150.25,
                'price_display': '$150.25',
                'market_cap': 2400000000000,
                'market_cap_display': '$2.4T',
                'momentum_value': 0.0523,
                'momentum_pct': 5.23,
                'momentum_display': '+5.23%',
                'ai_summary': 'Apple shares surged on strong iPhone sales...',
                'has_summary': True
            },
            {
                'ticker': 'MSFT',
                'company_name': 'Microsoft Corporation',
                'current_price': 280.50,
                'price_display': '$280.50',
                'market_cap': 2100000000000,
                'market_cap_display': '$2.1T',
                'momentum_value': -0.0234,
                'momentum_pct': -2.34,
                'momentum_display': '-2.34%',
                'ai_summary': '',
                'has_summary': False
            },
            {
                'ticker': 'GOOGL',
                'company_name': 'Alphabet Inc.',
                'current_price': 2500.00,
                'price_display': '$2500.00',
                'market_cap': 1800000000000,
                'market_cap_display': '$1.8T',
                'momentum_value': 0.0876,
                'momentum_pct': 8.76,
                'momentum_display': '+8.76%',
                'ai_summary': 'Google parent company benefits from AI advances...',
                'has_summary': True
            }
        ]
        
        self.sample_transformed_data = {
            'metadata': {
                'generated_at': '2026-03-01T16:30:00Z',
                'market_date': '2026-03-01',
                'data_version': '1.0'
            },
            'tiers': {
                '1T_plus': {
                    'timeframes': {
                        '7d': self.sample_stock_data,
                        '30d': self.sample_stock_data
                    },
                    'stats': {
                        '7d': {
                            'count': 3,
                            'avg_momentum': 0.0388,
                            'max_momentum': 0.0876,
                            'min_momentum': -0.0234,
                            'stocks_with_summaries': 2
                        }
                    }
                }
            },
            'summary': {
                'total_stocks': 3,
                'total_tiers': 1,
                'timeframes': ['7d', '30d'],
                'market_date': '2026-03-01',
                'last_updated': '2026-03-01T16:30:00Z'
            }
        }
    
    def test_tier_selector_functionality(self):
        """Test tier selector component."""
        tier_selector = TierSelector()
        
        # Test tier display names
        self.assertEqual(tier_selector.get_tier_display_name('100B_200B'), '$100B - $200B')
        self.assertEqual(tier_selector.get_tier_display_name('1T_plus'), '$1T+')
        self.assertEqual(tier_selector.get_tier_display_name('unknown'), 'unknown')
        
        # Test available tiers filtering
        available_tiers = ['100B_200B', '1T_plus']
        # Note: We can't test the actual render method without Streamlit context
        # but we can test the logic
        self.assertIn('100B_200B', tier_selector.tier_options)
        self.assertIn('1T_plus', tier_selector.tier_options)
    
    def test_timeframe_selector_functionality(self):
        """Test timeframe selector component."""
        timeframe_selector = TimeframeSelector()
        
        # Test timeframe display names
        self.assertEqual(timeframe_selector.get_timeframe_display_name('7d'), '7 Days')
        self.assertEqual(timeframe_selector.get_timeframe_display_name('90d'), '90 Days')
        self.assertEqual(timeframe_selector.get_timeframe_display_name('unknown'), 'unknown')
        
        # Test timeframe options
        self.assertIn('7d', timeframe_selector.timeframe_options)
        self.assertIn('90d', timeframe_selector.timeframe_options)
    
    def test_stock_ranking_table_data_processing(self):
        """Test stock ranking table data processing."""
        stock_table = StockRankingTable()
        
        # Test timeframe display conversion
        self.assertEqual(stock_table._get_timeframe_display('7d'), '7 Days')
        self.assertEqual(stock_table._get_timeframe_display('30d'), '30 Days')
    
    def test_filter_controls_logic(self):
        """Test filter controls logic."""
        # Test momentum range filtering
        test_stocks = self.sample_stock_data.copy()
        
        # Filter for positive momentum only
        positive_stocks = [s for s in test_stocks if s['momentum_value'] > 0]
        self.assertEqual(len(positive_stocks), 2)  # AAPL and GOOGL
        
        # Filter by momentum range
        high_momentum_stocks = [s for s in test_stocks if s['momentum_value'] > 0.05]
        self.assertEqual(len(high_momentum_stocks), 2)  # AAPL and GOOGL
        
        # Filter by AI summary availability
        stocks_with_summary = [s for s in test_stocks if s['has_summary']]
        self.assertEqual(len(stocks_with_summary), 2)  # AAPL and GOOGL
    
    def test_data_transformer_functionality(self):
        """Test data transformer methods."""
        transformer = DataTransformer()
        
        # Test stock DataFrame creation
        df = transformer.create_stock_dataframe(self.sample_stock_data, '7d')
        self.assertFalse(df.empty)
        self.assertEqual(len(df), 3)
        self.assertIn('Ticker', df.columns)
        self.assertIn('Momentum', df.columns)
        
        # Test tier summary creation
        tier_data = self.sample_transformed_data['tiers']['1T_plus']
        summary_df = transformer.create_tier_summary_dataframe(tier_data)
        self.assertFalse(summary_df.empty)
        self.assertIn('Timeframe', summary_df.columns)
        self.assertIn('Avg Momentum', summary_df.columns)
        
        # Test cross-tier comparison
        comparison_df = transformer.create_cross_tier_comparison(
            self.sample_transformed_data, '7d'
        )
        self.assertFalse(comparison_df.empty)
        self.assertIn('Tier', comparison_df.columns)
        self.assertIn('Top Performer', comparison_df.columns)
    
    def test_stock_filtering_and_sorting(self):
        """Test stock filtering and sorting functionality."""
        transformer = DataTransformer()
        
        # Test momentum filtering
        filtered_stocks = transformer.filter_stocks_by_criteria(
            self.sample_stock_data,
            min_momentum=0.0
        )
        self.assertEqual(len(filtered_stocks), 2)  # Only positive momentum stocks
        
        # Test market cap filtering
        filtered_stocks = transformer.filter_stocks_by_criteria(
            self.sample_stock_data,
            min_market_cap=2000000000000  # $2T minimum
        )
        self.assertEqual(len(filtered_stocks), 2)  # AAPL and MSFT
        
        # Test AI summary filtering
        filtered_stocks = transformer.filter_stocks_by_criteria(
            self.sample_stock_data,
            has_summary=True
        )
        self.assertEqual(len(filtered_stocks), 2)  # AAPL and GOOGL
        
        # Test sorting by momentum
        sorted_stocks = transformer.sort_stocks(
            self.sample_stock_data,
            sort_by='momentum',
            ascending=False
        )
        self.assertEqual(sorted_stocks[0]['ticker'], 'GOOGL')  # Highest momentum
        self.assertEqual(sorted_stocks[-1]['ticker'], 'MSFT')  # Lowest momentum
        
        # Test sorting by market cap
        sorted_stocks = transformer.sort_stocks(
            self.sample_stock_data,
            sort_by='market_cap',
            ascending=False
        )
        self.assertEqual(sorted_stocks[0]['ticker'], 'AAPL')  # Highest market cap
    
    def test_momentum_distribution_calculation(self):
        """Test momentum distribution statistics."""
        transformer = DataTransformer()
        
        distribution = transformer.calculate_momentum_distribution(self.sample_stock_data)
        
        self.assertEqual(distribution['count'], 3)
        self.assertEqual(distribution['positive_count'], 2)
        self.assertEqual(distribution['negative_count'], 1)
        self.assertEqual(distribution['zero_count'], 0)
        
        # Test percentiles
        self.assertIn('percentiles', distribution)
        self.assertIn('p50', distribution['percentiles'])  # Median
        
        # Test basic statistics
        self.assertAlmostEqual(distribution['mean'], 0.0388, places=4)
        self.assertEqual(distribution['max'], 0.0876)
        self.assertEqual(distribution['min'], -0.0234)
    
    def test_export_data_formatting(self):
        """Test data export formatting."""
        transformer = DataTransformer()
        
        export_data = transformer.format_data_for_export(
            self.sample_stock_data,
            '1T_plus',
            '7d'
        )
        
        self.assertIn('metadata', export_data)
        self.assertIn('stocks', export_data)
        
        # Test metadata
        metadata = export_data['metadata']
        self.assertEqual(metadata['tier'], '1T_plus')
        self.assertEqual(metadata['timeframe'], '7d')
        self.assertEqual(metadata['stock_count'], 3)
        
        # Test stock data
        stocks = export_data['stocks']
        self.assertEqual(len(stocks), 3)
        
        first_stock = stocks[0]
        self.assertEqual(first_stock['rank'], 1)
        self.assertIn('ticker', first_stock)
        self.assertIn('momentum_value', first_stock)
        self.assertIn('has_ai_summary', first_stock)
    
    def test_heatmap_data_creation(self):
        """Test heatmap data creation for visualization."""
        transformer = DataTransformer()
        
        heatmap_df = transformer.create_momentum_heatmap_data(self.sample_transformed_data)
        
        self.assertFalse(heatmap_df.empty)
        self.assertIn('$1T+', heatmap_df.index)  # Tier name as index
        
        # Check that timeframe columns exist
        expected_columns = ['7 Days', '30 Days', '60 Days', '90 Days']
        for col in expected_columns:
            if col in heatmap_df.columns:
                # At least some timeframe columns should exist
                break
        else:
            self.fail("No expected timeframe columns found in heatmap data")
    
    def test_anchor_alpha_theme_functionality(self):
        """Test AnchorAlpha theme functionality."""
        theme = AnchorAlphaTheme()
        
        # Test momentum formatting
        positive_momentum = theme.format_momentum_display(0.0523)
        self.assertIn('momentum-positive', positive_momentum)
        self.assertIn('+5.23%', positive_momentum)
        
        negative_momentum = theme.format_momentum_display(-0.0234)
        self.assertIn('momentum-negative', negative_momentum)
        self.assertIn('-2.34%', negative_momentum)
        
        zero_momentum = theme.format_momentum_display(0.0)
        self.assertIn('momentum-neutral', zero_momentum)
        self.assertIn('0.00%', zero_momentum)
        
        # Test tier badge creation
        tier_badge = theme.create_tier_badge('1T_plus')
        self.assertIn('$1T+', tier_badge)
        self.assertIn('tier-1t-plus', tier_badge)
        
        unknown_tier_badge = theme.create_tier_badge('unknown')
        self.assertIn('unknown', unknown_tier_badge)
    
    @patch('streamlit.session_state', {})
    def test_dashboard_filter_application(self):
        """Test dashboard filter application logic."""
        # Create a mock dashboard instance
        dashboard = MomentumDashboard()
        
        # Test filter application
        filter_values = {
            'momentum_min': 0.0,
            'momentum_max': 1.0,
            'positive_only': True,
            'summary_filter': 'With AI Summary'
        }
        
        filtered_stocks = dashboard._apply_filters(self.sample_stock_data, filter_values)
        
        # Should only include positive momentum stocks with AI summaries
        self.assertEqual(len(filtered_stocks), 2)  # AAPL and GOOGL
        
        for stock in filtered_stocks:
            self.assertGreater(stock['momentum_value'], 0)
            self.assertTrue(stock['has_summary'])
    
    def test_dashboard_data_validation(self):
        """Test dashboard data validation."""
        dashboard = MomentumDashboard()
        
        # Test available timeframes extraction
        timeframes = dashboard._get_available_timeframes(self.sample_transformed_data)
        self.assertIn('7d', timeframes)
        self.assertIn('30d', timeframes)
        
        # Test empty data handling
        empty_timeframes = dashboard._get_available_timeframes({})
        self.assertEqual(len(empty_timeframes), 0)
    
    def test_responsive_design_components(self):
        """Test responsive design functionality."""
        # Test mobile view detection and handling
        stock_table = StockRankingTable()
        
        # Test that mobile rendering method exists
        self.assertTrue(hasattr(stock_table, '_render_mobile_stock_cards'))
        
        # Test mobile card rendering logic (without Streamlit context)
        # This tests the data preparation for mobile cards
        test_stocks = self.sample_stock_data[:2]  # First 2 stocks
        
        # Verify that all required fields are present for mobile rendering
        for stock in test_stocks:
            self.assertIn('ticker', stock)
            self.assertIn('company_name', stock)
            self.assertIn('price_display', stock)
            self.assertIn('market_cap_display', stock)
            self.assertIn('momentum_value', stock)
            self.assertIn('has_summary', stock)
    
    def test_error_handling(self):
        """Test error handling in dashboard components."""
        transformer = DataTransformer()
        
        # Test empty data handling
        empty_df = transformer.create_stock_dataframe([], '7d')
        self.assertTrue(empty_df.empty)
        
        # Test invalid data handling
        invalid_stocks = [{'invalid': 'data'}]
        result_df = transformer.create_stock_dataframe(invalid_stocks, '7d')
        # Should handle gracefully and return empty or minimal DataFrame
        self.assertIsInstance(result_df, type(empty_df))
        
        # Test distribution calculation with empty data
        empty_distribution = transformer.calculate_momentum_distribution([])
        self.assertEqual(empty_distribution, {})
        
        # Test filtering with invalid criteria
        filtered_stocks = transformer.filter_stocks_by_criteria(
            self.sample_stock_data,
            min_momentum=None,  # Invalid filter
            max_momentum=None
        )
        # Should return original data when filters are invalid
        self.assertEqual(len(filtered_stocks), len(self.sample_stock_data))


class TestDashboardIntegration(unittest.TestCase):
    """Integration tests for dashboard components working together."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.sample_data = {
            'tiers': {
                '1T_plus': {
                    'timeframes': {
                        '7d': [
                            {
                                'ticker': 'AAPL',
                                'company_name': 'Apple Inc.',
                                'momentum_value': 0.05,
                                'has_summary': True,
                                'market_cap': 2400000000000
                            }
                        ]
                    }
                }
            }
        }
    
    def test_end_to_end_data_flow(self):
        """Test complete data flow from raw data to UI display."""
        # Simulate the data transformation pipeline
        transformer = DataTransformer()
        
        # Test that data can be processed through the full pipeline
        stocks = self.sample_data['tiers']['1T_plus']['timeframes']['7d']
        
        # Create DataFrame
        df = transformer.create_stock_dataframe(stocks, '7d')
        self.assertFalse(df.empty)
        
        # Apply filters
        filtered_stocks = transformer.filter_stocks_by_criteria(
            stocks,
            min_momentum=0.0
        )
        self.assertEqual(len(filtered_stocks), 1)
        
        # Sort stocks
        sorted_stocks = transformer.sort_stocks(
            filtered_stocks,
            sort_by='momentum'
        )
        self.assertEqual(len(sorted_stocks), 1)
        
        # Format for export
        export_data = transformer.format_data_for_export(
            sorted_stocks,
            '1T_plus',
            '7d'
        )
        self.assertIn('stocks', export_data)
        self.assertEqual(len(export_data['stocks']), 1)
    
    def test_component_interaction(self):
        """Test interaction between different UI components."""
        tier_selector = TierSelector()
        timeframe_selector = TimeframeSelector()
        
        # Test that components can work with the same data
        available_tiers = ['1T_plus']
        available_timeframes = ['7d', '30d']
        
        # Both components should handle the same available options
        tier_display = tier_selector.get_tier_display_name('1T_plus')
        timeframe_display = timeframe_selector.get_timeframe_display_name('7d')
        
        self.assertEqual(tier_display, '$1T+')
        self.assertEqual(timeframe_display, '7 Days')


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)