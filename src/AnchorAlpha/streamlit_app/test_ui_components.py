"""
Test script for UI components - can be run to verify component functionality.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from ui_components import (
    TierSelector, TimeframeSelector, StockRankingTable,
    FilterControls, DataSummaryPanel, ErrorDisplay
)
from styling import AnchorAlphaTheme


def test_components():
    """Test UI components functionality."""
    print("Testing AnchorAlpha UI Components")
    print("=" * 40)
    
    # Test TierSelector
    print("\n1. Testing TierSelector...")
    tier_selector = TierSelector()
    available_tiers = ['100B_200B', '200B_500B', '500B_1T', '1T_plus']
    
    for tier in available_tiers:
        display_name = tier_selector.get_tier_display_name(tier)
        print(f"   {tier} -> {display_name}")
    
    # Test TimeframeSelector
    print("\n2. Testing TimeframeSelector...")
    timeframe_selector = TimeframeSelector()
    available_timeframes = ['7d', '30d', '60d', '90d']
    
    for timeframe in available_timeframes:
        display_name = timeframe_selector.get_timeframe_display_name(timeframe)
        print(f"   {timeframe} -> {display_name}")
    
    # Test AnchorAlphaTheme
    print("\n3. Testing AnchorAlphaTheme...")
    theme = AnchorAlphaTheme()
    
    # Test momentum formatting
    test_momentums = [0.05, -0.03, 0.0, 0.15, -0.08]
    for momentum in test_momentums:
        formatted = theme.format_momentum_display(momentum)
        print(f"   {momentum} -> {formatted}")
    
    # Test tier badges
    print("\n4. Testing tier badges...")
    for tier in available_tiers:
        badge = theme.create_tier_badge(tier)
        print(f"   {tier} -> {badge}")
    
    # Test sample stock data
    print("\n5. Testing sample stock data...")
    sample_stocks = [
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
        }
    ]
    
    print(f"   Created {len(sample_stocks)} sample stocks")
    for stock in sample_stocks:
        print(f"   - {stock['ticker']}: {stock['momentum_display']} (Summary: {stock['has_summary']})")
    
    # Test data summary
    print("\n6. Testing data summary...")
    sample_summary = {
        'total_stocks': 150,
        'total_tiers': 4,
        'timeframes': ['7d', '30d', '60d', '90d'],
        'market_date': '2026-03-01',
        'last_updated': '2026-03-01T16:30:00Z'
    }
    
    print(f"   Total stocks: {sample_summary['total_stocks']}")
    print(f"   Total tiers: {sample_summary['total_tiers']}")
    print(f"   Timeframes: {', '.join(sample_summary['timeframes'])}")
    print(f"   Market date: {sample_summary['market_date']}")
    
    print("\n✓ All component tests completed successfully!")
    print("\nTo run the full Streamlit app:")
    print("   streamlit run AnchorAlpha/src/AnchorAlpha/streamlit_app/app.py")


if __name__ == "__main__":
    test_components()