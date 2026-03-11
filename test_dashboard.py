#!/usr/bin/env python3
"""
Simple test dashboard for AnchorAlpha momentum screener.
"""

import streamlit as st
import sys
import os
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from AnchorAlpha.api.fmp_client import FMPClient
from AnchorAlpha.momentum_engine import MomentumEngine

# Set page config
st.set_page_config(
    page_title="AnchorAlpha Momentum Screener",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme
st.markdown("""
<style>
    .main {
        background-color: #001f3f;
        color: #ffffff;
    }
    .stTitle {
        color: #FFD700;
        text-align: center;
    }
    .metric-card {
        background-color: #2c3e50;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #FFD700;
    }
</style>
""", unsafe_allow_html=True)

def main():
    # Title with logo
    st.markdown("""
    <h1 style='text-align: center; color: #FFD700;'>
        ⚓ AnchorAlpha α
    </h1>
    <h3 style='text-align: center; color: #ffffff;'>
        Large-Cap Momentum Screener
    </h3>
    """, unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.markdown("## 📊 Controls")
    
    # Test API connection
    if st.sidebar.button("🧪 Test API Connection"):
        with st.spinner("Testing FMP API..."):
            try:
                # Get API key from environment
                api_key = os.getenv('FMP_API_KEY', 'zGnf89XHdjXeCKtYEswNXxB2UT51iBBP')
                client = FMPClient(api_key)
                
                # Test with Apple
                profile = client.get_company_profile('AAPL')
                
                st.success(f"✅ API Connected: {profile.get('companyName', 'N/A')}")
                st.json({
                    "Company": profile.get('companyName'),
                    "Market Cap": f"${profile.get('marketCap', 0):,}",
                    "Price": f"${profile.get('price', 0):.2f}",
                    "Sector": profile.get('sector', 'N/A')
                })
                
            except Exception as e:
                st.error(f"❌ API Error: {str(e)}")
    
    # Market cap tiers
    st.sidebar.markdown("## 🏢 Market Cap Tiers")
    tier = st.sidebar.selectbox(
        "Select Tier:",
        ["$100B - $200B", "$200B - $500B", "$500B - $1T", "$1T+"]
    )
    
    # Time windows
    st.sidebar.markdown("## ⏰ Momentum Window")
    timeframe = st.sidebar.selectbox(
        "Select Timeframe:",
        ["7 days", "30 days", "60 days", "90 days"]
    )
    
    # Main content
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h4>📈 Selected Tier</h4>
            <p style="font-size: 1.2em; color: #FFD700;">{}</p>
        </div>
        """.format(tier), unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <h4>⏱️ Time Window</h4>
            <p style="font-size: 1.2em; color: #FFD700;">{}</p>
        </div>
        """.format(timeframe), unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <h4>🎯 Status</h4>
            <p style="font-size: 1.2em; color: #00ff00;">Ready</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Sample data table
    st.markdown("## 📊 Top Momentum Stocks")
    
    # Create sample data
    import pandas as pd
    sample_data = pd.DataFrame({
        'Symbol': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'],
        'Company': ['Apple Inc.', 'Microsoft Corp.', 'Alphabet Inc.', 'Amazon.com Inc.', 'Tesla Inc.'],
        'Price': ['$260.83', '$405.76', '$142.50', '$185.20', '$195.30'],
        'Market Cap': ['$3.8T', '$3.0T', '$1.8T', '$1.9T', '$620B'],
        'Momentum %': ['+12.5%', '+8.3%', '+15.2%', '+6.7%', '+22.1%']
    })
    
    st.dataframe(
        sample_data,
        use_container_width=True,
        hide_index=True
    )
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #888888;'>
        <p>AnchorAlpha - Professional Momentum Screening Platform</p>
        <p>Powered by Financial Modeling Prep API</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()