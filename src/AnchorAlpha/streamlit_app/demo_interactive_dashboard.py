"""
Demo script to showcase the interactive dashboard functionality.
This can be run to demonstrate the dashboard features without requiring S3 data.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from ui_components import (
    TierSelector, TimeframeSelector, StockRankingTable, 
    FilterControls, DataSummaryPanel, create_sidebar_controls
)
from styling import AnchorAlphaTheme, apply_custom_theme
from data_transforms import DataTransformer


def create_demo_data():
    """Create sample data for demonstration."""
    demo_stocks = [
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
            'ai_summary': 'Apple shares surged on strong iPhone sales and services growth, with analysts praising the company\'s AI integration strategy.',
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
            'ai_summary': 'Google parent company benefits from AI advances and strong cloud growth, with search revenue remaining robust.',
            'has_summary': True
        },
        {
            'ticker': 'AMZN',
            'company_name': 'Amazon.com Inc.',
            'current_price': 3200.00,
            'price_display': '$3200.00',
            'market_cap': 1600000000000,
            'market_cap_display': '$1.6T',
            'momentum_value': 0.0345,
            'momentum_pct': 3.45,
            'momentum_display': '+3.45%',
            'ai_summary': 'Amazon shows strong momentum driven by AWS growth and improved retail margins, with logistics efficiency gains.',
            'has_summary': True
        },
        {
            'ticker': 'TSLA',
            'company_name': 'Tesla Inc.',
            'current_price': 800.00,
            'price_display': '$800.00',
            'market_cap': 800000000000,
            'market_cap_display': '$800.0B',
            'momentum_value': 0.1234,
            'momentum_pct': 12.34,
            'momentum_display': '+12.34%',
            'ai_summary': 'Tesla stock rallies on strong delivery numbers and progress in autonomous driving technology.',
            'has_summary': True
        }
    ]
    
    return {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'market_date': '2026-03-01',
            'data_version': '1.0'
        },
        'tiers': {
            '1T_plus': {
                'timeframes': {
                    '7d': demo_stocks[:3],
                    '30d': demo_stocks[:3],
                    '60d': demo_stocks[:3],
                    '90d': demo_stocks[:3]
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
            },
            '500B_1T': {
                'timeframes': {
                    '7d': demo_stocks[3:],
                    '30d': demo_stocks[3:],
                    '60d': demo_stocks[3:],
                    '90d': demo_stocks[3:]
                },
                'stats': {
                    '7d': {
                        'count': 2,
                        'avg_momentum': 0.0789,
                        'max_momentum': 0.1234,
                        'min_momentum': 0.0345,
                        'stocks_with_summaries': 2
                    }
                }
            }
        },
        'summary': {
            'total_stocks': 5,
            'total_tiers': 2,
            'timeframes': ['7d', '30d', '60d', '90d'],
            'market_date': '2026-03-01',
            'last_updated': datetime.now().isoformat()
        }
    }


def main():
    """Main demo application."""
    # Configure page
    st.set_page_config(
        page_title="AnchorAlpha Demo - Interactive Dashboard",
        page_icon="⚓",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Apply theme
    apply_custom_theme()
    
    # Create header
    AnchorAlphaTheme.create_logo_header()
    
    st.markdown("### 🚀 Interactive Dashboard Demo")
    st.info("This is a demonstration of the AnchorAlpha interactive dashboard with sample data.")
    
    # Create demo data
    demo_data = create_demo_data()
    
    # Initialize components
    tier_selector = TierSelector()
    timeframe_selector = TimeframeSelector()
    stock_table = StockRankingTable()
    filter_controls = FilterControls()
    summary_panel = DataSummaryPanel()
    transformer = DataTransformer()
    
    # Display data summary
    st.subheader("📊 Market Overview")
    summary_panel.render(demo_data['summary'])
    
    # Create sidebar controls
    st.sidebar.header("🎛️ Dashboard Controls")
    
    available_tiers = list(demo_data['tiers'].keys())
    available_timeframes = ['7d', '30d', '60d', '90d']
    
    selected_tier, selected_timeframe = create_sidebar_controls(
        available_tiers, available_timeframes
    )
    
    # Add mobile view toggle
    st.sidebar.markdown("---")
    mobile_view = st.sidebar.checkbox("📱 Mobile View", help="Toggle mobile-friendly display")
    
    # Add advanced filters
    st.sidebar.markdown("---")
    filter_values = filter_controls.render("demo")
    
    # Main content area
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("📈 Stock Rankings")
        
        # Display content based on selections
        if selected_tier == 'all' and selected_timeframe == 'all':
            st.info("Showing overview of all tiers and timeframes")
            
            # Create tabs for different views
            tab1, tab2 = st.tabs(["Cross-Tier Comparison", "Top Performers"])
            
            with tab1:
                st.subheader("Performance Comparison")
                for timeframe in available_timeframes:
                    comparison_df = transformer.create_cross_tier_comparison(demo_data, timeframe)
                    if not comparison_df.empty:
                        with st.expander(f"{timeframe_selector.get_timeframe_display_name(timeframe)} Comparison"):
                            st.dataframe(comparison_df, use_container_width=True)
            
            with tab2:
                st.subheader("Top Performers Across All Categories")
                all_stocks = []
                for tier_key, tier_data in demo_data['tiers'].items():
                    for tf, stocks in tier_data['timeframes'].items():
                        for stock in stocks[:3]:  # Top 3 from each
                            stock_copy = stock.copy()
                            stock_copy['tier_display'] = tier_selector.get_tier_display_name(tier_key)
                            stock_copy['timeframe_display'] = timeframe_selector.get_timeframe_display_name(tf)
                            all_stocks.append(stock_copy)
                
                # Sort by momentum and display top 10
                all_stocks.sort(key=lambda x: x['momentum_value'], reverse=True)
                top_stocks = all_stocks[:10]
                
                for i, stock in enumerate(top_stocks, 1):
                    with st.container():
                        scol1, scol2, scol3 = st.columns([1, 2, 1])
                        
                        with scol1:
                            st.write(f"**#{i}**")
                        
                        with scol2:
                            st.write(f"**{stock['ticker']}** - {stock['company_name']}")
                            st.caption(f"{stock['tier_display']} | {stock['timeframe_display']}")
                        
                        with scol3:
                            momentum_html = AnchorAlphaTheme.format_momentum_display(stock['momentum_value'])
                            st.markdown(momentum_html, unsafe_allow_html=True)
                        
                        st.markdown("---")
        
        else:
            # Display specific tier/timeframe combination
            if selected_tier != 'all':
                tier_data = demo_data['tiers'].get(selected_tier, {})
                
                if selected_timeframe != 'all':
                    # Specific tier and timeframe
                    stocks = tier_data.get('timeframes', {}).get(selected_timeframe, [])
                    
                    if stocks:
                        # Apply filters
                        filtered_stocks = apply_demo_filters(stocks, filter_values)
                        
                        if filtered_stocks:
                            tier_display = tier_selector.get_tier_display_name(selected_tier)
                            timeframe_display = timeframe_selector.get_timeframe_display_name(selected_timeframe)
                            
                            st.write(f"**{tier_display} - {timeframe_display}**")
                            
                            # Display metrics
                            mcol1, mcol2, mcol3 = st.columns(3)
                            
                            with mcol1:
                                AnchorAlphaTheme.create_metric_card("Total Stocks", str(len(filtered_stocks)))
                            
                            with mcol2:
                                avg_momentum = sum(s['momentum_value'] for s in filtered_stocks) / len(filtered_stocks)
                                AnchorAlphaTheme.create_metric_card("Avg Momentum", f"{avg_momentum * 100:+.2f}%")
                            
                            with mcol3:
                                with_summaries = sum(1 for s in filtered_stocks if s['has_summary'])
                                AnchorAlphaTheme.create_metric_card("With AI Summary", f"{with_summaries}/{len(filtered_stocks)}")
                            
                            # Display stock table
                            if mobile_view:
                                # Mobile card layout
                                for i, stock in enumerate(filtered_stocks, 1):
                                    with st.container():
                                        rcol1, rcol2 = st.columns([3, 1])
                                        
                                        with rcol1:
                                            st.markdown(f"**#{i} {stock['ticker']}** - {stock['company_name']}")
                                            st.caption(f"Price: {stock['price_display']} | Cap: {stock['market_cap_display']}")
                                        
                                        with rcol2:
                                            momentum_html = AnchorAlphaTheme.format_momentum_display(stock['momentum_value'])
                                            st.markdown(momentum_html, unsafe_allow_html=True)
                                            if stock['has_summary']:
                                                st.success("AI ✓")
                                            else:
                                                st.info("No AI")
                                        
                                        st.markdown("---")
                            else:
                                # Desktop table layout
                                selected_stock = stock_table.render(filtered_stocks, selected_timeframe, show_summaries=True)
                        else:
                            st.warning("No stocks match the current filter criteria.")
                    else:
                        st.warning("No data available for the selected combination.")
                else:
                    # All timeframes for specific tier
                    st.write(f"**{tier_selector.get_tier_display_name(selected_tier)} - All Timeframes**")
                    
                    for tf in available_timeframes:
                        stocks = tier_data.get('timeframes', {}).get(tf, [])
                        if stocks:
                            filtered_stocks = apply_demo_filters(stocks, filter_values)
                            if filtered_stocks:
                                with st.expander(f"{timeframe_selector.get_timeframe_display_name(tf)} ({len(filtered_stocks)} stocks)"):
                                    stock_table.render(filtered_stocks[:5], tf, show_summaries=False, max_rows=5)
    
    with col2:
        st.subheader("📋 Dashboard Info")
        
        st.info(f"""
        **Current Selection:**
        - Tier: {tier_selector.get_tier_display_name(selected_tier) if selected_tier != 'all' else 'All Tiers'}
        - Timeframe: {timeframe_selector.get_timeframe_display_name(selected_timeframe) if selected_timeframe != 'all' else 'All Timeframes'}
        - Mobile View: {'Yes' if mobile_view else 'No'}
        """)
        
        st.markdown("---")
        
        st.subheader("🎯 Filter Summary")
        st.write(f"**Momentum Range:** {filter_values['momentum_min']*100:.0f}% to {filter_values['momentum_max']*100:.0f}%")
        st.write(f"**Positive Only:** {'Yes' if filter_values['positive_only'] else 'No'}")
        st.write(f"**AI Summary Filter:** {filter_values['summary_filter']}")
        
        st.markdown("---")
        
        st.subheader("🔧 Features Demonstrated")
        st.write("✅ Interactive tier selection")
        st.write("✅ Dynamic timeframe filtering")
        st.write("✅ Advanced momentum filters")
        st.write("✅ Responsive mobile design")
        st.write("✅ AI summary display")
        st.write("✅ Real-time data updates")
        st.write("✅ Cross-tier comparisons")
        st.write("✅ Export-ready formatting")
    
    # Footer
    st.markdown("---")
    AnchorAlphaTheme.create_footer()


def apply_demo_filters(stocks, filter_values):
    """Apply filters to demo stocks."""
    filtered_stocks = stocks.copy()
    
    # Apply momentum range filter
    momentum_min = filter_values.get('momentum_min', -1.0)
    momentum_max = filter_values.get('momentum_max', 2.0)
    
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


if __name__ == "__main__":
    main()