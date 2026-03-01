"""
Streamlit styling and theming for AnchorAlpha application.
"""

import streamlit as st
from typing import Dict, Any


class AnchorAlphaTheme:
    """AnchorAlpha dark mode theme configuration."""
    
    # Color palette
    NAVY_BLUE = "#001f3f"
    GOLD = "#FFD700"
    SLATE_GRAY = "#708090"
    DARK_GRAY = "#2F2F2F"
    LIGHT_GRAY = "#E8E8E8"
    WHITE = "#FFFFFF"
    SUCCESS_GREEN = "#28a745"
    WARNING_ORANGE = "#fd7e14"
    ERROR_RED = "#dc3545"
    
    # Typography
    FONT_FAMILY = "Arial, sans-serif"
    HEADER_FONT = "Georgia, serif"
    
    @classmethod
    def apply_theme(cls):
        """Apply the AnchorAlpha dark theme to Streamlit."""
        
        # Custom CSS for dark theme
        css = f"""
        <style>
        /* Main app background */
        .stApp {{
            background-color: {cls.NAVY_BLUE};
            color: {cls.WHITE};
            font-family: {cls.FONT_FAMILY};
        }}
        
        /* Responsive design */
        @media (max-width: 768px) {{
            .main-title {{
                font-size: 2rem !important;
            }}
            
            .subtitle {{
                font-size: 1rem !important;
            }}
            
            .logo {{
                font-size: 2rem !important;
            }}
            
            .metric-card {{
                margin-bottom: 0.5rem;
                padding: 0.75rem;
            }}
            
            .metric-value {{
                font-size: 1.5rem;
            }}
            
            .stock-summary {{
                padding: 0.75rem;
            }}
        }}
        
        @media (max-width: 480px) {{
            .main-title {{
                font-size: 1.5rem !important;
            }}
            
            .subtitle {{
                font-size: 0.9rem !important;
            }}
            
            .logo {{
                font-size: 1.5rem !important;
            }}
            
            .metric-card {{
                padding: 0.5rem;
            }}
            
            .metric-value {{
                font-size: 1.2rem;
            }}
        }}
        
        /* Sidebar styling */
        .css-1d391kg {{
            background-color: {cls.DARK_GRAY};
        }}
        
        /* Headers */
        h1, h2, h3, h4, h5, h6 {{
            color: {cls.GOLD};
            font-family: {cls.HEADER_FONT};
        }}
        
        /* Main title styling */
        .main-title {{
            color: {cls.GOLD};
            font-size: 3rem;
            font-weight: bold;
            text-align: center;
            margin-bottom: 0.5rem;
            font-family: {cls.HEADER_FONT};
        }}
        
        /* Subtitle styling */
        .subtitle {{
            color: {cls.SLATE_GRAY};
            font-size: 1.2rem;
            text-align: center;
            margin-bottom: 2rem;
            font-style: italic;
        }}
        
        /* Logo styling */
        .logo {{
            font-size: 2.5rem;
            color: {cls.GOLD};
            text-align: center;
            margin-bottom: 1rem;
        }}
        
        /* Metric cards */
        .metric-card {{
            background-color: {cls.DARK_GRAY};
            padding: 1rem;
            border-radius: 8px;
            border-left: 4px solid {cls.GOLD};
            margin-bottom: 1rem;
        }}
        
        .metric-value {{
            font-size: 2rem;
            font-weight: bold;
            color: {cls.GOLD};
        }}
        
        .metric-label {{
            color: {cls.SLATE_GRAY};
            font-size: 0.9rem;
            text-transform: uppercase;
        }}
        
        /* Data tables */
        .dataframe {{
            background-color: {cls.DARK_GRAY};
            color: {cls.WHITE};
            width: 100%;
            overflow-x: auto;
        }}
        
        .dataframe th {{
            background-color: {cls.NAVY_BLUE};
            color: {cls.GOLD};
            font-weight: bold;
            padding: 0.75rem 0.5rem;
        }}
        
        .dataframe td {{
            background-color: {cls.DARK_GRAY};
            color: {cls.WHITE};
            padding: 0.5rem;
        }}
        
        /* Responsive table */
        @media (max-width: 768px) {{
            .dataframe {{
                font-size: 0.8rem;
            }}
            
            .dataframe th, .dataframe td {{
                padding: 0.25rem;
            }}
        }}
        
        /* Mobile-friendly table wrapper */
        .table-container {{
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }}
        
        /* Positive momentum styling */
        .momentum-positive {{
            color: {cls.SUCCESS_GREEN};
            font-weight: bold;
        }}
        
        /* Negative momentum styling */
        .momentum-negative {{
            color: {cls.ERROR_RED};
            font-weight: bold;
        }}
        
        /* Neutral momentum styling */
        .momentum-neutral {{
            color: {cls.SLATE_GRAY};
        }}
        
        /* Selection boxes */
        .stSelectbox > div > div {{
            background-color: {cls.DARK_GRAY};
            color: {cls.WHITE};
        }}
        
        /* Buttons */
        .stButton > button {{
            background-color: {cls.GOLD};
            color: {cls.NAVY_BLUE};
            border: none;
            border-radius: 4px;
            font-weight: bold;
        }}
        
        .stButton > button:hover {{
            background-color: {cls.WHITE};
            color: {cls.NAVY_BLUE};
        }}
        
        /* Info boxes */
        .info-box {{
            background-color: {cls.DARK_GRAY};
            padding: 1rem;
            border-radius: 8px;
            border: 1px solid {cls.SLATE_GRAY};
            margin: 1rem 0;
        }}
        
        /* Warning boxes */
        .warning-box {{
            background-color: {cls.WARNING_ORANGE}20;
            padding: 1rem;
            border-radius: 8px;
            border-left: 4px solid {cls.WARNING_ORANGE};
            margin: 1rem 0;
        }}
        
        /* Error boxes */
        .error-box {{
            background-color: {cls.ERROR_RED}20;
            padding: 1rem;
            border-radius: 8px;
            border-left: 4px solid {cls.ERROR_RED};
            margin: 1rem 0;
        }}
        
        /* Stock summary cards */
        .stock-summary {{
            background-color: {cls.DARK_GRAY};
            padding: 1rem;
            border-radius: 8px;
            border: 1px solid {cls.SLATE_GRAY};
            margin-bottom: 1rem;
        }}
        
        .stock-ticker {{
            color: {cls.GOLD};
            font-weight: bold;
            font-size: 1.2rem;
        }}
        
        .stock-company {{
            color: {cls.SLATE_GRAY};
            font-size: 0.9rem;
        }}
        
        /* Tier badges */
        .tier-badge {{
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: bold;
            margin-right: 0.5rem;
        }}
        
        .tier-100b-200b {{
            background-color: {cls.SUCCESS_GREEN};
            color: {cls.WHITE};
        }}
        
        .tier-200b-500b {{
            background-color: {cls.WARNING_ORANGE};
            color: {cls.WHITE};
        }}
        
        .tier-500b-1t {{
            background-color: {cls.ERROR_RED};
            color: {cls.WHITE};
        }}
        
        .tier-1t-plus {{
            background-color: {cls.GOLD};
            color: {cls.NAVY_BLUE};
        }}
        
        /* Loading spinner */
        .loading-spinner {{
            text-align: center;
            color: {cls.GOLD};
            font-size: 1.2rem;
        }}
        
        /* Footer */
        .footer {{
            text-align: center;
            color: {cls.SLATE_GRAY};
            font-size: 0.8rem;
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid {cls.SLATE_GRAY};
        }}
        </style>
        """
        
        st.markdown(css, unsafe_allow_html=True)
    
    @classmethod
    def create_logo_header(cls):
        """Create the AnchorAlpha logo and header."""
        st.markdown(
            f"""
            <div class="logo">
                ⚓ AnchorAlpha α
            </div>
            <div class="main-title">
                Momentum Screener
            </div>
            <div class="subtitle">
                Institutional-Grade Large-Cap Analysis
            </div>
            """,
            unsafe_allow_html=True
        )
    
    @classmethod
    def create_metric_card(cls, label: str, value: str, delta: str = None):
        """Create a styled metric card."""
        delta_html = ""
        if delta:
            delta_color = cls.SUCCESS_GREEN if delta.startswith('+') else cls.ERROR_RED
            delta_html = f'<div style="color: {delta_color}; font-size: 0.9rem;">{delta}</div>'
        
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
                {delta_html}
            </div>
            """,
            unsafe_allow_html=True
        )
    
    @classmethod
    def format_momentum_display(cls, momentum_value: float) -> str:
        """Format momentum value with appropriate styling."""
        momentum_pct = momentum_value * 100
        
        if momentum_pct > 0:
            css_class = "momentum-positive"
            sign = "+"
        elif momentum_pct < 0:
            css_class = "momentum-negative"
            sign = ""
        else:
            css_class = "momentum-neutral"
            sign = ""
        
        return f'<span class="{css_class}">{sign}{momentum_pct:.2f}%</span>'
    
    @classmethod
    def create_tier_badge(cls, tier_key: str) -> str:
        """Create a styled tier badge."""
        tier_names = {
            '100B_200B': ('$100B-$200B', 'tier-100b-200b'),
            '200B_500B': ('$200B-$500B', 'tier-200b-500b'),
            '500B_1T': ('$500B-$1T', 'tier-500b-1t'),
            '1T_plus': ('$1T+', 'tier-1t-plus')
        }
        
        display_name, css_class = tier_names.get(tier_key, (tier_key, 'tier-badge'))
        return f'<span class="tier-badge {css_class}">{display_name}</span>'
    
    @classmethod
    def create_info_box(cls, content: str, box_type: str = "info"):
        """Create a styled info box."""
        css_class = f"{box_type}-box"
        st.markdown(
            f'<div class="{css_class}">{content}</div>',
            unsafe_allow_html=True
        )
    
    @classmethod
    def create_stock_summary_card(cls, stock: Dict[str, Any]):
        """Create a styled stock summary card."""
        ticker = stock.get('ticker', '')
        company = stock.get('company_name', '')
        price = stock.get('price_display', '')
        market_cap = stock.get('market_cap_display', '')
        momentum = stock.get('momentum_display', '')
        summary = stock.get('ai_summary', '')
        
        momentum_html = cls.format_momentum_display(stock.get('momentum_value', 0))
        
        summary_html = ""
        if summary:
            summary_html = f'<div style="margin-top: 0.5rem; font-style: italic; color: {cls.SLATE_GRAY};">{summary}</div>'
        
        st.markdown(
            f"""
            <div class="stock-summary">
                <div class="stock-ticker">{ticker}</div>
                <div class="stock-company">{company}</div>
                <div style="margin-top: 0.5rem;">
                    <strong>Price:</strong> {price} | 
                    <strong>Market Cap:</strong> {market_cap} | 
                    <strong>Momentum:</strong> {momentum_html}
                </div>
                {summary_html}
            </div>
            """,
            unsafe_allow_html=True
        )
    
    @classmethod
    def create_footer(cls):
        """Create the application footer."""
        st.markdown(
            f"""
            <div class="footer">
                AnchorAlpha © 2026 | Powered by Financial Modeling Prep & Perplexity AI
            </div>
            """,
            unsafe_allow_html=True
        )


def apply_custom_theme():
    """Apply the AnchorAlpha theme to the Streamlit app."""
    AnchorAlphaTheme.apply_theme()


def create_loading_spinner(message: str = "Loading data..."):
    """Create a loading spinner with message."""
    st.markdown(
        f'<div class="loading-spinner">⚓ {message}</div>',
        unsafe_allow_html=True
    )