"""
Main AnchorAlpha momentum screening dashboard.
"""

import streamlit as st
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

try:
    from .data_loader import get_data_loader
    from .data_transforms import DataTransformer
    from .ui_components import (
        TierSelector, TimeframeSelector, StockRankingTable, 
        FilterControls, DataSummaryPanel, ErrorDisplay,
        create_sidebar_controls, create_main_dashboard_layout
    )
    from .styling import AnchorAlphaTheme, apply_custom_theme, create_loading_spinner
except ImportError:
    from data_loader import get_data_loader
    from data_transforms import DataTransformer
    from ui_components import (
        TierSelector, TimeframeSelector, StockRankingTable, 
        FilterControls, DataSummaryPanel, ErrorDisplay,
        create_sidebar_controls, create_main_dashboard_layout
    )
    from styling import AnchorAlphaTheme, apply_custom_theme, create_loading_spinner


logger = logging.getLogger(__name__)


class MomentumDashboard:
    """Main dashboard class for AnchorAlpha momentum screening."""
    
    def __init__(self):
        """Initialize the dashboard."""
        self.data_loader = get_data_loader()
        self.data_transformer = DataTransformer()
        self.theme = AnchorAlphaTheme()
        
        # UI components
        self.tier_selector = TierSelector()
        self.timeframe_selector = TimeframeSelector()
        self.stock_table = StockRankingTable()
        self.filter_controls = FilterControls()
        self.summary_panel = DataSummaryPanel()
        self.error_display = ErrorDisplay()
    
    def run(self):
        """Run the main dashboard application."""
        # Configure page
        st.set_page_config(
            page_title="AnchorAlpha - Momentum Screener",
            page_icon="⚓",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Detect mobile view (simple heuristic)
        if 'mobile_view' not in st.session_state:
            st.session_state.mobile_view = False
        
        # Add mobile view toggle in sidebar
        with st.sidebar:
            st.session_state.mobile_view = st.checkbox(
                "Mobile View", 
                value=st.session_state.mobile_view,
                help="Toggle mobile-friendly display"
            )
        
        # Apply custom theme
        apply_custom_theme()
        
        # Create main layout
        main_container = create_main_dashboard_layout()
        
        with main_container:
            # Load and display data
            self._load_and_display_data()
    
    def _load_and_display_data(self):
        """Load data and display the dashboard with enhanced error handling."""
        try:
            # Check for any existing error states
            error_state = self.data_loader.get_error_state()
            if error_state.get('has_error', False):
                self.error_display.render_error({
                    'error': True,
                    'error_type': error_state.get('error_type', 'Unknown'),
                    'error_message': error_state.get('error_message', 'Unknown error'),
                    'suggestions': self._get_error_suggestions(error_state.get('error_type', ''))
                })
                return
            
            # Show loading state
            loading_info = self.data_loader.get_loading_progress()
            if loading_info.get('is_loading', False):
                self.error_display.render_loading_state(loading_info)
            
            # Show loading spinner with custom message
            with st.spinner("🔄 Loading momentum data from cloud storage..."):
                raw_data = self.data_loader.load_latest_momentum_data()
            
            if not raw_data:
                # Check if there's a specific error state
                error_state = self.data_loader.get_error_state()
                if error_state.get('has_error', False):
                    error_info = {
                        'error': True,
                        'error_type': error_state.get('error_type', 'No Data'),
                        'error_message': error_state.get('error_message', 'No data available'),
                        'suggestions': self._get_error_suggestions(error_state.get('error_type', ''))
                    }
                    self.error_display.render_error(error_info)
                else:
                    self.error_display.render_no_data_message()
                return
            
            # Validate data freshness with enhanced feedback
            data_age_hours = self._calculate_data_age(raw_data)
            if not self.data_loader.validate_data_freshness(raw_data):
                self.error_display.render_warning(
                    f"Data is {data_age_hours:.1f} hours old and may be outdated. Latest market data processing may still be in progress.",
                    "data_stale"
                )
            
            # Transform data for UI with error handling
            try:
                transformed_data = self.data_loader.transform_data_for_ui(raw_data)
            except Exception as transform_error:
                logger.error(f"Data transformation error: {transform_error}")
                st.error("Error processing momentum data. Please try refreshing the page.")
                return
            
            if not transformed_data:
                st.error("Error processing momentum data for display.")
                return
            
            # Check data quality and show warnings
            data_quality_issues = self._check_overall_data_quality(transformed_data)
            if data_quality_issues:
                self.error_display.render_data_quality_warning(data_quality_issues)
            
            # Display connection status
            self.error_display.render_connection_status(
                is_connected=True,
                last_update=transformed_data.get('metadata', {}).get('generated_at')
            )
            
            # Display data summary
            self.summary_panel.render(transformed_data.get('summary', {}))
            
            # Get available options for filters
            available_tiers = list(transformed_data.get('tiers', {}).keys())
            available_timeframes = self._get_available_timeframes(transformed_data)
            
            if not available_tiers or not available_timeframes:
                self.error_display.render_warning(
                    "Limited data available. Some tiers or timeframes may be missing.",
                    "partial_data"
                )
                if not available_tiers and not available_timeframes:
                    return
            
            # Create sidebar controls
            selected_tier, selected_timeframe = create_sidebar_controls(
                available_tiers, available_timeframes
            )
            
            # Add advanced filters to sidebar
            st.sidebar.markdown("---")
            filter_values = self.filter_controls.render("sidebar")
            
            # Display main content based on selections
            self._display_filtered_content(
                transformed_data, selected_tier, selected_timeframe, filter_values
            )
            
            # Create footer
            self.theme.create_footer()
            
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            error_info = self.data_loader.handle_data_loading_error(e)
            error_info['suggestions'] = self._get_error_suggestions('dashboard_error')
            self.error_display.render_error(error_info)
    
    def _get_error_suggestions(self, error_type: str) -> List[str]:
        """Get contextual error suggestions based on error type."""
        suggestions_map = {
            'no_data': [
                "Check if it's a weekend or market holiday",
                "Wait 10-15 minutes for data processing to complete",
                "Try refreshing the page",
                "Contact support if the issue persists"
            ],
            'corrupted_data': [
                "Try refreshing the page to load alternative data",
                "Check back in a few minutes for updated data",
                "Contact support if data corruption persists"
            ],
            'loading_error': [
                "Check your internet connection",
                "Verify AWS service availability",
                "Try refreshing the page",
                "Contact support if the issue continues"
            ],
            'dates_error': [
                "Check AWS credentials and permissions",
                "Verify S3 bucket configuration",
                "Try refreshing the page",
                "Contact support for configuration help"
            ],
            'dashboard_error': [
                "Try refreshing the page",
                "Clear your browser cache",
                "Check your internet connection",
                "Contact support if the problem persists"
            ]
        }
        
        return suggestions_map.get(error_type, [
            "Try refreshing the page",
            "Check your internet connection",
            "Contact support if the issue persists"
        ])
    
    def _calculate_data_age(self, data: Dict[str, Any]) -> float:
        """Calculate data age in hours."""
        try:
            generated_at = data.get('generated_at', '')
            if generated_at:
                generated_time = datetime.fromisoformat(generated_at.replace('Z', '+00:00'))
                age = datetime.now(generated_time.tzinfo) - generated_time
                return age.total_seconds() / 3600
        except Exception:
            pass
        return 0.0
    
    def _check_overall_data_quality(self, transformed_data: Dict[str, Any]) -> List[str]:
        """Check overall data quality across all tiers and timeframes."""
        issues = []
        
        tiers = transformed_data.get('tiers', {})
        if not tiers:
            return issues
        
        total_stocks = 0
        stocks_with_summaries = 0
        empty_tiers = 0
        
        for tier_name, tier_data in tiers.items():
            timeframes = tier_data.get('timeframes', {})
            if not timeframes:
                empty_tiers += 1
                continue
            
            for timeframe, stocks in timeframes.items():
                total_stocks += len(stocks)
                stocks_with_summaries += sum(1 for s in stocks if s.get('has_summary', False))
        
        # Check for empty tiers
        if empty_tiers > 0:
            issues.append(f"{empty_tiers} market cap tiers have no data available")
        
        # Check AI summary coverage
        if total_stocks > 0:
            summary_coverage = (stocks_with_summaries / total_stocks) * 100
            if summary_coverage < 30:
                issues.append(f"Only {summary_coverage:.0f}% of stocks have AI summaries (API limitations may apply)")
        
        return issues
    
    def _get_available_timeframes(self, transformed_data: Dict[str, Any]) -> List[str]:
        """Extract available timeframes from transformed data."""
        timeframes = set()
        
        for tier_data in transformed_data.get('tiers', {}).values():
            timeframes.update(tier_data.get('timeframes', {}).keys())
        
        # Sort timeframes by duration
        timeframe_order = ['7d', '30d', '60d', '90d']
        return [tf for tf in timeframe_order if tf in timeframes]
    
    def _display_filtered_content(self, 
                                transformed_data: Dict[str, Any],
                                selected_tier: str,
                                selected_timeframe: str,
                                filter_values: Dict[str, Any]):
        """Display content based on current filter selections."""
        
        if selected_tier == 'all' and selected_timeframe == 'all':
            self._display_overview(transformed_data, filter_values)
        elif selected_tier == 'all':
            self._display_timeframe_view(transformed_data, selected_timeframe, filter_values)
        elif selected_timeframe == 'all':
            self._display_tier_view(transformed_data, selected_tier, filter_values)
        else:
            self._display_specific_view(transformed_data, selected_tier, selected_timeframe, filter_values)
    
    def _display_overview(self, transformed_data: Dict[str, Any], filter_values: Dict[str, Any]):
        """Display overview of all tiers and timeframes."""
        st.header("Market Overview - All Tiers & Timeframes")
        
        # Create tabs for different views
        tab1, tab2, tab3 = st.tabs(["Cross-Tier Comparison", "Tier Breakdown", "Top Performers"])
        
        with tab1:
            self._display_cross_tier_comparison(transformed_data)
        
        with tab2:
            self._display_tier_breakdown(transformed_data, filter_values)
        
        with tab3:
            self._display_top_performers_overview(transformed_data, filter_values)
    
    def _display_timeframe_view(self, 
                              transformed_data: Dict[str, Any],
                              timeframe: str,
                              filter_values: Dict[str, Any]):
        """Display view for specific timeframe across all tiers."""
        timeframe_display = self.timeframe_selector.get_timeframe_display_name(timeframe)
        st.header(f"Market Analysis - {timeframe_display}")
        
        # Create cross-tier comparison for this timeframe
        comparison_df = self.data_transformer.create_cross_tier_comparison(
            transformed_data, timeframe
        )
        
        if not comparison_df.empty:
            st.subheader("Tier Performance Comparison")
            st.dataframe(comparison_df, use_container_width=True)
        
        # Display top performers for each tier
        st.subheader("Top Performers by Tier")
        
        for tier_key, tier_data in transformed_data.get('tiers', {}).items():
            if timeframe not in tier_data.get('timeframes', {}):
                continue
            
            tier_display = self.tier_selector.get_tier_display_name(tier_key)
            stocks = tier_data['timeframes'][timeframe]
            
            # Apply filters
            filtered_stocks = self._apply_filters(stocks, filter_values)
            
            if filtered_stocks:
                with st.expander(f"{tier_display} ({len(filtered_stocks)} stocks)", expanded=True):
                    self.stock_table.render(
                        filtered_stocks[:10], timeframe, show_summaries=False, max_rows=10
                    )
    
    def _display_tier_view(self, 
                         transformed_data: Dict[str, Any],
                         tier: str,
                         filter_values: Dict[str, Any]):
        """Display view for specific tier across all timeframes."""
        tier_display = self.tier_selector.get_tier_display_name(tier)
        st.header(f"Tier Analysis - {tier_display}")
        
        tier_data = transformed_data.get('tiers', {}).get(tier, {})
        
        if not tier_data:
            st.warning(f"No data available for {tier_display}")
            return
        
        # Create tier summary
        summary_df = self.data_transformer.create_tier_summary_dataframe(tier_data)
        
        if not summary_df.empty:
            st.subheader("Timeframe Performance Summary")
            st.dataframe(summary_df, use_container_width=True)
        
        # Display stocks for each timeframe
        st.subheader("Top Performers by Timeframe")
        
        for timeframe, stocks in tier_data.get('timeframes', {}).items():
            timeframe_display = self.timeframe_selector.get_timeframe_display_name(timeframe)
            
            # Apply filters
            filtered_stocks = self._apply_filters(stocks, filter_values)
            
            if filtered_stocks:
                with st.expander(f"{timeframe_display} ({len(filtered_stocks)} stocks)", expanded=True):
                    self.stock_table.render(
                        filtered_stocks[:10], timeframe, show_summaries=False, max_rows=10
                    )
    
    def _display_specific_view(self, 
                             transformed_data: Dict[str, Any],
                             tier: str,
                             timeframe: str,
                             filter_values: Dict[str, Any]):
        """Display view for specific tier and timeframe combination."""
        tier_display = self.tier_selector.get_tier_display_name(tier)
        timeframe_display = self.timeframe_selector.get_timeframe_display_name(timeframe)
        
        st.header(f"{tier_display} - {timeframe_display}")
        
        # Get stocks for this combination
        tier_data = transformed_data.get('tiers', {}).get(tier, {})
        stocks = tier_data.get('timeframes', {}).get(timeframe, [])
        
        if not stocks:
            st.warning(f"No stocks available for {tier_display} in {timeframe_display} timeframe.")
            return
        
        # Apply filters
        filtered_stocks = self._apply_filters(stocks, filter_values)
        
        if not filtered_stocks:
            st.warning("No stocks match the current filter criteria.")
            return
        
        # Display statistics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            self.theme.create_metric_card(
                "Total Stocks",
                str(len(filtered_stocks))
            )
        
        with col2:
            avg_momentum = sum(s.get('momentum_value', 0) for s in filtered_stocks) / len(filtered_stocks)
            self.theme.create_metric_card(
                "Avg Momentum",
                f"{avg_momentum * 100:+.2f}%"
            )
        
        with col3:
            stocks_with_summaries = sum(1 for s in filtered_stocks if s.get('has_summary', False))
            self.theme.create_metric_card(
                "With AI Summary",
                f"{stocks_with_summaries}/{len(filtered_stocks)}"
            )
        
        # Display stock ranking table with enhanced error handling
        st.subheader("Stock Rankings")
        selected_stock = self.stock_table.render_with_error_handling(
            filtered_stocks, timeframe, show_summaries=True
        )
    
    def _display_cross_tier_comparison(self, transformed_data: Dict[str, Any]):
        """Display cross-tier comparison for all timeframes."""
        st.subheader("Performance Comparison Across Tiers")
        
        for timeframe in ['7d', '30d', '60d', '90d']:
            comparison_df = self.data_transformer.create_cross_tier_comparison(
                transformed_data, timeframe
            )
            
            if not comparison_df.empty:
                timeframe_display = self.timeframe_selector.get_timeframe_display_name(timeframe)
                with st.expander(f"{timeframe_display} Comparison", expanded=False):
                    st.dataframe(comparison_df, use_container_width=True)
    
    def _display_tier_breakdown(self, transformed_data: Dict[str, Any], filter_values: Dict[str, Any]):
        """Display breakdown of each tier."""
        st.subheader("Tier-by-Tier Breakdown")
        
        for tier_key, tier_data in transformed_data.get('tiers', {}).items():
            tier_display = self.tier_selector.get_tier_display_name(tier_key)
            
            with st.expander(f"{tier_display}", expanded=False):
                summary_df = self.data_transformer.create_tier_summary_dataframe(tier_data)
                if not summary_df.empty:
                    st.dataframe(summary_df, use_container_width=True)
    
    def _display_top_performers_overview(self, transformed_data: Dict[str, Any], filter_values: Dict[str, Any]):
        """Display top performers across all tiers and timeframes."""
        st.subheader("Top Performers Across All Categories")
        
        # Collect top performers from each tier/timeframe combination
        all_performers = []
        
        for tier_key, tier_data in transformed_data.get('tiers', {}).items():
            for timeframe, stocks in tier_data.get('timeframes', {}).items():
                filtered_stocks = self._apply_filters(stocks[:5], filter_values)  # Top 5 from each
                
                for stock in filtered_stocks:
                    stock_copy = stock.copy()
                    stock_copy['tier_display'] = self.tier_selector.get_tier_display_name(tier_key)
                    stock_copy['timeframe_display'] = self.timeframe_selector.get_timeframe_display_name(timeframe)
                    all_performers.append(stock_copy)
        
        # Sort by momentum and take top 20
        all_performers.sort(key=lambda x: x.get('momentum_value', 0), reverse=True)
        top_performers = all_performers[:20]
        
        if top_performers:
            # Create a simplified table for top performers
            for i, stock in enumerate(top_performers, 1):
                with st.container():
                    col1, col2, col3, col4 = st.columns([1, 3, 2, 2])
                    
                    with col1:
                        st.write(f"**#{i}**")
                    
                    with col2:
                        st.write(f"**{stock['ticker']}** - {stock['company_name']}")
                        st.caption(f"{stock['tier_display']} | {stock['timeframe_display']}")
                    
                    with col3:
                        momentum_html = self.theme.format_momentum_display(stock.get('momentum_value', 0))
                        st.markdown(momentum_html, unsafe_allow_html=True)
                    
                    with col4:
                        if stock.get('has_summary', False):
                            st.success("AI Summary ✓")
                        else:
                            st.info("No Summary")
                    
                    st.markdown("---")
    
    def _apply_filters(self, stocks: List[Dict[str, Any]], filter_values: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply filter criteria to stock list."""
        if not stocks or not filter_values:
            return stocks
        
        filtered_stocks = stocks.copy()
        
        # Apply momentum range filter with None handling
        momentum_min = filter_values.get('momentum_min', -1.0)
        momentum_max = filter_values.get('momentum_max', 2.0)
        
        # Handle None values in filter criteria
        if momentum_min is None:
            momentum_min = -1.0
        if momentum_max is None:
            momentum_max = 2.0
        
        filtered_stocks = [
            s for s in filtered_stocks 
            if momentum_min <= s.get('momentum_value', 0) <= momentum_max
        ]
        
        # Apply positive momentum filter
        if filter_values.get('positive_only', False):
            filtered_stocks = [
                s for s in filtered_stocks 
                if s.get('momentum_value', 0) > 0
            ]
        
        # Apply AI summary filter
        summary_filter = filter_values.get('summary_filter', 'All Stocks')
        if summary_filter == 'With AI Summary':
            filtered_stocks = [s for s in filtered_stocks if s.get('has_summary', False)]
        elif summary_filter == 'Without AI Summary':
            filtered_stocks = [s for s in filtered_stocks if not s.get('has_summary', False)]
        
        return filtered_stocks


def main():
    """Main entry point for the dashboard application."""
    dashboard = MomentumDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()