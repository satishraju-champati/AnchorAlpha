"""
Streamlit UI components for AnchorAlpha application.
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
import logging

try:
    from .styling import AnchorAlphaTheme
except ImportError:
    from styling import AnchorAlphaTheme


logger = logging.getLogger(__name__)


class TierSelector:
    """Component for market cap tier selection."""
    
    def __init__(self):
        self.tier_options = {
            'all': 'All Tiers',
            '100B_200B': '$100B - $200B',
            '200B_500B': '$200B - $500B',
            '500B_1T': '$500B - $1T',
            '1T_plus': '$1T+'
        }
    
    def render(self, available_tiers: List[str], key: str = "tier_selector") -> str:
        """
        Render tier selection component.
        
        Args:
            available_tiers: List of available tier keys
            key: Unique key for the component
            
        Returns:
            Selected tier key
        """
        # Filter options to only show available tiers
        filtered_options = {'all': 'All Tiers'}
        for tier_key in available_tiers:
            if tier_key in self.tier_options:
                filtered_options[tier_key] = self.tier_options[tier_key]
        
        # Create selectbox
        selected_display = st.selectbox(
            "Select Market Cap Tier",
            options=list(filtered_options.values()),
            index=0,
            key=key,
            help="Filter stocks by market capitalization tier"
        )
        
        # Return the key corresponding to the selected display name
        for key_val, display_val in filtered_options.items():
            if display_val == selected_display:
                return key_val
        
        return 'all'
    
    def get_tier_display_name(self, tier_key: str) -> str:
        """Get display name for a tier key."""
        return self.tier_options.get(tier_key, tier_key)


class TimeframeSelector:
    """Component for momentum timeframe selection."""
    
    def __init__(self):
        self.timeframe_options = {
            'all': 'All Timeframes',
            '7d': '7 Days',
            '30d': '30 Days',
            '60d': '60 Days',
            '90d': '90 Days'
        }
    
    def render(self, available_timeframes: List[str], key: str = "timeframe_selector") -> str:
        """
        Render timeframe selection component.
        
        Args:
            available_timeframes: List of available timeframe keys
            key: Unique key for the component
            
        Returns:
            Selected timeframe key
        """
        # Filter options to only show available timeframes
        filtered_options = {'all': 'All Timeframes'}
        for timeframe_key in available_timeframes:
            if timeframe_key in self.timeframe_options:
                filtered_options[timeframe_key] = self.timeframe_options[timeframe_key]
        
        # Create selectbox
        selected_display = st.selectbox(
            "Select Momentum Timeframe",
            options=list(filtered_options.values()),
            index=0,
            key=key,
            help="Select the time window for momentum calculations"
        )
        
        # Return the key corresponding to the selected display name
        for key_val, display_val in filtered_options.items():
            if display_val == selected_display:
                return key_val
        
        return 'all'
    
    def get_timeframe_display_name(self, timeframe_key: str) -> str:
        """Get display name for a timeframe key."""
        return self.timeframe_options.get(timeframe_key, timeframe_key)


class StockRankingTable:
    """Component for displaying stock rankings with sortable columns."""
    
    def __init__(self):
        self.theme = AnchorAlphaTheme()
    
    def render(self, 
               stocks: List[Dict[str, Any]], 
               timeframe: str,
               show_summaries: bool = True,
               max_rows: int = 20) -> Optional[Dict[str, Any]]:
        """
        Render stock ranking table with sortable columns.
        
        Args:
            stocks: List of stock dictionaries
            timeframe: Current timeframe for display
            show_summaries: Whether to show AI summaries
            max_rows: Maximum number of rows to display
            
        Returns:
            Selected stock data or None
        """
        if not stocks:
            st.warning("No stocks available for the selected criteria.")
            return None
        
        try:
            # Create DataFrame for display
            df_data = []
            for i, stock in enumerate(stocks[:max_rows], 1):
                momentum_value = stock.get('momentum_value', 0)
                momentum_html = self.theme.format_momentum_display(momentum_value)
                
                row = {
                    'Rank': i,
                    'Ticker': stock.get('ticker', ''),
                    'Company': stock.get('company_name', ''),
                    'Price': stock.get('price_display', ''),
                    'Market Cap': stock.get('market_cap_display', ''),
                    'Momentum': momentum_html,
                    'AI Summary': '✓' if stock.get('has_summary', False) else '✗'
                }
                df_data.append(row)
            
            df = pd.DataFrame(df_data)
            
            # Display table header
            st.subheader(f"Top {len(df)} Performers - {self._get_timeframe_display(timeframe)}")
            
            # Check if mobile view
            is_mobile = st.session_state.get('mobile_view', False)
            
            if is_mobile:
                # Mobile-friendly card layout
                self._render_mobile_stock_cards(stocks[:max_rows], timeframe)
            else:
                # Desktop table layout with responsive wrapper
                st.markdown('<div class="table-container">', unsafe_allow_html=True)
                st.markdown(df.to_html(escape=False, index=False), unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Show stock selection for detailed view
            if show_summaries and len(stocks) > 0:
                st.subheader("Stock Details")
                
                # Create selection options
                stock_options = [f"{stock['ticker']} - {stock['company_name']}" 
                               for stock in stocks[:max_rows]]
                
                selected_option = st.selectbox(
                    "Select a stock for detailed information:",
                    options=["Select a stock..."] + stock_options,
                    key="stock_detail_selector"
                )
                
                if selected_option != "Select a stock...":
                    # Find the selected stock
                    ticker = selected_option.split(' - ')[0]
                    selected_stock = next((s for s in stocks if s['ticker'] == ticker), None)
                    
                    if selected_stock:
                        self._render_stock_detail(selected_stock)
                        return selected_stock
            
            return None
            
        except Exception as e:
            logger.error(f"Error rendering stock ranking table: {e}")
            st.error("Error displaying stock rankings. Please try again.")
            return None
    
    def _render_mobile_stock_cards(self, stocks: List[Dict[str, Any]], timeframe: str):
        """Render stocks as mobile-friendly cards."""
        for i, stock in enumerate(stocks, 1):
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"**#{i} {stock['ticker']}** - {stock['company_name']}")
                    st.caption(f"Price: {stock['price_display']} | Cap: {stock['market_cap_display']}")
                
                with col2:
                    momentum_html = self.theme.format_momentum_display(stock.get('momentum_value', 0))
                    st.markdown(momentum_html, unsafe_allow_html=True)
                    if stock.get('has_summary', False):
                        st.success("AI ✓")
                    else:
                        st.info("No AI")
                
                st.markdown("---")
    
    def _render_stock_detail(self, stock: Dict[str, Any]):
        """Render detailed view of a selected stock with enhanced error handling."""
        try:
            # Create stock summary card
            self.theme.create_stock_summary_card(stock)
            
            # Enhanced AI summary handling
            if stock.get('has_summary', False) and stock.get('ai_summary'):
                st.subheader("🤖 AI Analysis: Why It's Moving")
                
                # Check if summary is placeholder or actual content
                ai_summary = stock['ai_summary'].strip()
                if ai_summary and len(ai_summary) > 10:  # Basic content validation
                    st.markdown(
                        f'<div class="info-box">{ai_summary}</div>',
                        unsafe_allow_html=True
                    )
                    
                    # Add disclaimer
                    st.caption("💡 AI-generated insights are for informational purposes only and should not be considered as investment advice.")
                else:
                    self._render_summary_placeholder(stock['ticker'], "empty_summary")
            else:
                self._render_summary_placeholder(stock['ticker'], "no_summary")
            
            # Add manual research suggestions
            self._render_research_suggestions(stock)
                
        except Exception as e:
            logger.error(f"Error rendering stock detail: {e}")
            st.error("Error displaying stock details. Please try selecting another stock.")
            
            # Provide fallback information
            if stock.get('ticker'):
                st.info(f"You can research {stock['ticker']} manually using financial news sources.")
    
    def _render_summary_placeholder(self, ticker: str, reason: str):
        """Render placeholder when AI summary is unavailable."""
        reason_messages = {
            "no_summary": "AI summary is not available for this stock.",
            "empty_summary": "AI summary appears to be empty or invalid.",
            "api_error": "AI summary service is temporarily unavailable.",
            "rate_limit": "AI summary service rate limit reached."
        }
        
        message = reason_messages.get(reason, "AI summary is currently unavailable.")
        
        st.markdown(f"""
        <div style="
            background-color: #f8f9fa; 
            border: 2px dashed #dee2e6; 
            padding: 20px; 
            margin: 16px 0; 
            border-radius: 8px;
            text-align: center;
        ">
            <h5 style="color: #6c757d; margin: 0 0 12px 0;">🤖 AI Summary Unavailable</h5>
            <p style="margin: 0 0 12px 0; color: #6c757d;">
                {message}
            </p>
            <p style="margin: 0; color: #6c757d; font-size: 0.9em;">
                💡 Try checking financial news sources for insights on <strong>{ticker}</strong>
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    def _render_research_suggestions(self, stock: Dict[str, Any]):
        """Render manual research suggestions."""
        ticker = stock.get('ticker', '')
        
        if not ticker:
            return
        
        with st.expander("📚 Manual Research Resources", expanded=False):
            st.markdown(f"""
            **Research {ticker} using these resources:**
            
            • **Financial News:** Search for recent news about {ticker}
            • **SEC Filings:** Check recent 10-K, 10-Q, and 8-K filings
            • **Earnings Reports:** Review latest quarterly earnings
            • **Analyst Reports:** Look for recent analyst coverage
            • **Industry Analysis:** Research the company's sector trends
            
            **Key metrics to consider:**
            • Revenue growth trends
            • Profit margins and profitability
            • Debt levels and financial health
            • Market position and competitive advantages
            • Recent business developments or partnerships
            """)
            
            # Add external links (if appropriate for your use case)
            st.markdown(f"""
            **Quick Links:**
            - [Yahoo Finance](https://finance.yahoo.com/quote/{ticker})
            - [SEC EDGAR](https://www.sec.gov/edgar/searchedgar/companysearch.html)
            - [Google Finance](https://www.google.com/finance/quote/{ticker})
            """)
    
    def render_with_error_handling(self, 
                                 stocks: List[Dict[str, Any]], 
                                 timeframe: str,
                                 show_summaries: bool = True,
                                 max_rows: int = 20) -> Optional[Dict[str, Any]]:
        """
        Enhanced render method with comprehensive error handling.
        
        Args:
            stocks: List of stock dictionaries
            timeframe: Current timeframe for display
            show_summaries: Whether to show AI summaries
            max_rows: Maximum number of rows to display
            
        Returns:
            Selected stock data or None
        """
        # Input validation
        if not isinstance(stocks, list):
            st.error("Invalid stock data format received.")
            return None
        
        if not stocks:
            self._render_no_stocks_message()
            return None
        
        # Data quality checks
        data_issues = self._check_data_quality(stocks)
        if data_issues:
            self._render_data_quality_warnings(data_issues)
        
        # Filter out invalid stocks
        valid_stocks = self._filter_valid_stocks(stocks)
        
        if not valid_stocks:
            st.error("No valid stock data available for display.")
            return None
        
        # Proceed with normal rendering
        return self.render(valid_stocks, timeframe, show_summaries, max_rows)
    
    def _render_no_stocks_message(self):
        """Render message when no stocks are available."""
        st.markdown("""
        <div style="
            background-color: #f8f9fa; 
            border: 2px dashed #dee2e6; 
            padding: 24px; 
            margin: 16px 0; 
            border-radius: 8px;
            text-align: center;
        ">
            <h4 style="color: #6c757d; margin: 0 0 12px 0;">📈 No Stocks Available</h4>
            <p style="margin: 0; color: #6c757d;">
                No stocks match the current filter criteria or data is unavailable.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.info("💡 Try adjusting your filters or check back later for updated data.")
    
    def _check_data_quality(self, stocks: List[Dict[str, Any]]) -> List[str]:
        """Check data quality and return list of issues."""
        issues = []
        
        if not stocks:
            return issues
        
        # Check for missing required fields
        required_fields = ['ticker', 'company_name', 'momentum_value']
        missing_fields = set()
        
        for stock in stocks:
            for field in required_fields:
                if field not in stock or stock[field] is None:
                    missing_fields.add(field)
        
        if missing_fields:
            issues.append(f"Some stocks are missing data for: {', '.join(missing_fields)}")
        
        # Check for AI summary availability
        stocks_with_summaries = sum(1 for s in stocks if s.get('has_summary', False))
        summary_percentage = (stocks_with_summaries / len(stocks)) * 100
        
        if summary_percentage < 50:
            issues.append(f"Only {summary_percentage:.0f}% of stocks have AI summaries available")
        
        # Check for extreme momentum values (potential data errors)
        extreme_momentum = [s for s in stocks if s.get('momentum_value') is not None and abs(s.get('momentum_value', 0)) > 1.0]  # >100%
        if extreme_momentum:
            issues.append(f"{len(extreme_momentum)} stocks have extreme momentum values (>100%)")
        
        return issues
    
    def _render_data_quality_warnings(self, issues: List[str]):
        """Render data quality warnings."""
        if not issues:
            return
        
        st.markdown("""
        <div style="
            background-color: #fff3cd; 
            border-left: 4px solid #ffc107; 
            padding: 12px; 
            margin: 12px 0; 
            border-radius: 4px;
        ">
            <h5 style="color: #856404; margin: 0 0 8px 0;">⚠️ Data Quality Notice</h5>
        </div>
        """, unsafe_allow_html=True)
        
        for issue in issues:
            st.markdown(f"• {issue}")
    
    def _filter_valid_stocks(self, stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out stocks with invalid or missing critical data."""
        valid_stocks = []
        
        for stock in stocks:
            # Check if stock is a dictionary first
            if not isinstance(stock, dict):
                logger.warning(f"Filtering out non-dict stock data: {type(stock)}")
                continue
            
            # Check for required fields
            if (stock.get('ticker') and 
                stock.get('company_name') and 
                stock.get('momentum_value') is not None):
                valid_stocks.append(stock)
            else:
                logger.warning(f"Filtering out invalid stock data: {stock}")
        
        return valid_stocks
    
    def _get_timeframe_display(self, timeframe: str) -> str:
        """Get display name for timeframe."""
        timeframe_names = {
            '7d': '7 Days',
            '30d': '30 Days',
            '60d': '60 Days',
            '90d': '90 Days'
        }
        return timeframe_names.get(timeframe, timeframe)


class FilterControls:
    """Component for additional filtering controls."""
    
    def render(self, key_prefix: str = "filter") -> Dict[str, Any]:
        """
        Render additional filter controls.
        
        Args:
            key_prefix: Prefix for component keys
            
        Returns:
            Dictionary of filter values
        """
        st.subheader("Advanced Filters")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Momentum range filter
            momentum_range = st.slider(
                "Momentum Range (%)",
                min_value=-50.0,
                max_value=100.0,
                value=(-50.0, 100.0),
                step=1.0,
                key=f"{key_prefix}_momentum_range",
                help="Filter stocks by momentum percentage range"
            )
        
        with col2:
            # AI summary filter
            summary_filter = st.selectbox(
                "AI Summary Availability",
                options=["All Stocks", "With AI Summary", "Without AI Summary"],
                key=f"{key_prefix}_summary_filter",
                help="Filter stocks by AI summary availability"
            )
        
        # Additional options
        show_only_positive = st.checkbox(
            "Show only positive momentum",
            key=f"{key_prefix}_positive_only",
            help="Display only stocks with positive momentum"
        )
        
        return {
            'momentum_min': momentum_range[0] / 100,
            'momentum_max': momentum_range[1] / 100,
            'summary_filter': summary_filter,
            'positive_only': show_only_positive
        }


class DataSummaryPanel:
    """Component for displaying data summary and statistics."""
    
    def __init__(self):
        self.theme = AnchorAlphaTheme()
    
    def render(self, summary_data: Dict[str, Any]):
        """
        Render data summary panel.
        
        Args:
            summary_data: Summary statistics from transformed data
        """
        if not summary_data:
            return
        
        st.subheader("Market Overview")
        
        # Create metric cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            self.theme.create_metric_card(
                "Total Stocks",
                str(summary_data.get('total_stocks', 0))
            )
        
        with col2:
            self.theme.create_metric_card(
                "Market Tiers",
                str(summary_data.get('total_tiers', 0))
            )
        
        with col3:
            timeframes = summary_data.get('timeframes', [])
            self.theme.create_metric_card(
                "Timeframes",
                str(len(timeframes))
            )
        
        with col4:
            market_date = summary_data.get('market_date', 'N/A')
            self.theme.create_metric_card(
                "Market Date",
                market_date
            )
        
        # Show last updated info
        last_updated = summary_data.get('last_updated')
        if last_updated:
            st.caption(f"Last updated: {last_updated}")


class ErrorDisplay:
    """Component for displaying errors and warnings."""
    
    def __init__(self):
        self.theme = AnchorAlphaTheme()
    
    def render_error(self, error_info: Dict[str, Any]):
        """Render error information with enhanced user feedback."""
        if not error_info.get('error', False):
            return
        
        error_type = error_info.get('error_type', 'Unknown')
        error_message = error_info.get('error_message', 'Unknown error occurred')
        suggestions = error_info.get('suggestions', [])
        
        # Create error container with custom styling
        with st.container():
            st.markdown("""
            <div style="
                background-color: #ffebee; 
                border-left: 4px solid #f44336; 
                padding: 16px; 
                margin: 16px 0; 
                border-radius: 4px;
            ">
                <h4 style="color: #c62828; margin: 0 0 8px 0;">⚠️ Data Loading Error</h4>
                <p style="margin: 0 0 8px 0; color: #424242;"><strong>Error Type:</strong> {}</p>
                <p style="margin: 0; color: #424242;"><strong>Details:</strong> {}</p>
            </div>
            """.format(error_type, error_message), unsafe_allow_html=True)
        
        # Display suggestions if available
        if suggestions:
            st.subheader("💡 Troubleshooting Suggestions")
            for i, suggestion in enumerate(suggestions, 1):
                st.markdown(f"**{i}.** {suggestion}")
            
            # Add refresh button
            if st.button("🔄 Try Again", key=f"error_refresh_btn_{error_type}"):
                st.rerun()
    
    def render_warning(self, message: str, warning_type: str = "general"):
        """Render warning message with appropriate styling."""
        warning_styles = {
            "general": {"color": "#ff9800", "icon": "⚠️"},
            "data_stale": {"color": "#ff5722", "icon": "⏰"},
            "partial_data": {"color": "#2196f3", "icon": "ℹ️"},
            "performance": {"color": "#9c27b0", "icon": "🐌"}
        }
        
        style = warning_styles.get(warning_type, warning_styles["general"])
        
        st.markdown(f"""
        <div style="
            background-color: #fff3e0; 
            border-left: 4px solid {style['color']}; 
            padding: 12px; 
            margin: 12px 0; 
            border-radius: 4px;
        ">
            <p style="margin: 0; color: #424242;">
                <strong>{style['icon']} Warning:</strong> {message}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    def render_no_data_message(self):
        """Render enhanced message when no data is available."""
        st.markdown("""
        <div style="
            background-color: #f3e5f5; 
            border: 2px dashed #9c27b0; 
            padding: 24px; 
            margin: 24px 0; 
            border-radius: 8px;
            text-align: center;
        ">
            <h3 style="color: #7b1fa2; margin: 0 0 16px 0;">📊 No Data Available</h3>
            <p style="color: #424242; margin: 0 0 16px 0;">
                We couldn't find any momentum data to display right now.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Expandable troubleshooting section
        with st.expander("🔧 Troubleshooting Steps", expanded=False):
            st.markdown("""
            **Possible causes and solutions:**
            
            1. **Data Processing in Progress**
               - The daily data processing may still be running
               - Try refreshing in 10-15 minutes
            
            2. **No Recent Market Data**
               - Market may be closed or no trading data available
               - Check if it's a weekend or market holiday
            
            3. **Storage Connectivity Issues**
               - Temporary connection issues with data storage
               - Try refreshing the page
            
            4. **Configuration Issues**
               - AWS credentials or permissions may need updating
               - Contact support if the issue persists
            """)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Refresh Data", key="no_data_refresh"):
                    st.rerun()
            
            with col2:
                if st.button("📧 Contact Support", key="contact_support"):
                    st.info("Please contact support at support@anchoralpha.com")
    
    def render_loading_state(self, loading_info: Dict[str, Any]):
        """Render loading state with progress indicators."""
        if not loading_info.get('is_loading', False):
            return
        
        current_step = loading_info.get('current_step', 'Loading...')
        progress = loading_info.get('progress_pct', 0)
        
        # Create loading container
        with st.container():
            st.markdown(f"""
            <div style="
                background-color: #e3f2fd; 
                border-left: 4px solid #2196f3; 
                padding: 16px; 
                margin: 16px 0; 
                border-radius: 4px;
            ">
                <h4 style="color: #1976d2; margin: 0 0 8px 0;">⏳ Loading Data...</h4>
                <p style="margin: 0; color: #424242;">{current_step}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Progress bar if progress is available
            if progress > 0:
                st.progress(progress / 100)
    
    def render_fallback_summary(self, stock_ticker: str):
        """Render fallback display when AI summary is unavailable."""
        st.markdown(f"""
        <div style="
            background-color: #f5f5f5; 
            border: 1px solid #e0e0e0; 
            padding: 16px; 
            margin: 8px 0; 
            border-radius: 4px;
        ">
            <h5 style="color: #616161; margin: 0 0 8px 0;">🤖 AI Summary Unavailable</h5>
            <p style="margin: 0; color: #757575; font-style: italic;">
                AI-generated insights for {stock_ticker} are currently unavailable. 
                This could be due to API limitations or temporary service issues.
            </p>
            <p style="margin: 8px 0 0 0; color: #757575; font-size: 0.9em;">
                💡 <strong>Tip:</strong> Check back later for updated AI insights, or research 
                this stock manually using financial news sources.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    def render_data_quality_warning(self, issues: List[str]):
        """Render warning about data quality issues."""
        if not issues:
            return
        
        st.markdown("""
        <div style="
            background-color: #fff8e1; 
            border-left: 4px solid #ffc107; 
            padding: 16px; 
            margin: 16px 0; 
            border-radius: 4px;
        ">
            <h4 style="color: #f57c00; margin: 0 0 8px 0;">⚠️ Data Quality Notice</h4>
            <p style="margin: 0 0 8px 0; color: #424242;">
                Some data quality issues were detected:
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        for issue in issues:
            st.markdown(f"• {issue}")
        
        st.info("💡 Data is still usable, but results may be incomplete in some areas.")
    
    def render_connection_status(self, is_connected: bool, last_update: Optional[str] = None):
        """Render connection status indicator."""
        if is_connected:
            status_color = "#4caf50"
            status_icon = "🟢"
            status_text = "Connected"
        else:
            status_color = "#f44336"
            status_icon = "🔴"
            status_text = "Disconnected"
        
        st.markdown(f"""
        <div style="
            background-color: #fafafa; 
            border: 1px solid #e0e0e0; 
            padding: 8px 12px; 
            margin: 8px 0; 
            border-radius: 4px;
            display: flex;
            align-items: center;
            font-size: 0.9em;
        ">
            <span style="color: {status_color}; margin-right: 8px;">{status_icon}</span>
            <span style="color: #424242;">
                <strong>Data Connection:</strong> {status_text}
                {f" | Last Update: {last_update}" if last_update else ""}
            </span>
        </div>
        """, unsafe_allow_html=True)


# Utility functions for component integration
def create_sidebar_controls(available_tiers: List[str], 
                          available_timeframes: List[str]) -> Tuple[str, str]:
    """
    Create sidebar controls for tier and timeframe selection.
    
    Args:
        available_tiers: List of available tier keys
        available_timeframes: List of available timeframe keys
        
    Returns:
        Tuple of (selected_tier, selected_timeframe)
    """
    st.sidebar.header("Filters")
    
    # Tier selector
    tier_selector = TierSelector()
    selected_tier = tier_selector.render(available_tiers, "sidebar_tier")
    
    # Timeframe selector
    timeframe_selector = TimeframeSelector()
    selected_timeframe = timeframe_selector.render(available_timeframes, "sidebar_timeframe")
    
    return selected_tier, selected_timeframe


def create_main_dashboard_layout():
    """Create the main dashboard layout structure."""
    # Apply theme
    AnchorAlphaTheme.apply_theme()
    
    # Create header
    AnchorAlphaTheme.create_logo_header()
    
    # Create main content area
    main_container = st.container()
    
    return main_container