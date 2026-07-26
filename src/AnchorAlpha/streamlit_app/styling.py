"""
Streamlit styling for AnchorAlpha — dark/black professional theme.
"""

import streamlit as st
from typing import Dict, Any

# ── Color palette ──────────────────────────────────────────────────────────────
ACCENT      = "#3b82f6"       # primary blue accent
ACCENT_DIM  = "#1e3a5f"       # hover / subtle bg
DARK        = "#ffffff"       # headers / heavy text (white on black)
BODY        = "#e2e8f0"       # body text
MUTED       = "#94a3b8"       # secondary / labels
BORDER      = "#2d3748"       # borders
BG          = "#0a0a0f"       # page background (near black)
BG_ALT      = "#111827"       # card / alternating row bg
BG_CARD     = "#1a2035"       # elevated card bg
GREEN       = "#22c55e"       # positive
RED         = "#ef4444"       # negative
ORANGE      = "#f59e0b"       # warning


class AnchorAlphaTheme:
    """Dark/black professional theme."""

    NAVY_BLUE       = BG
    GOLD            = ACCENT
    SLATE_GRAY      = MUTED
    DARK_GRAY       = BG_ALT
    LIGHT_GRAY      = BORDER
    WHITE           = DARK
    SUCCESS_GREEN   = GREEN
    WARNING_ORANGE  = ORANGE
    ERROR_RED       = RED

    FONT_FAMILY  = "'Inter', 'Segoe UI', Arial, sans-serif"
    HEADER_FONT  = "'Inter', 'Segoe UI', Arial, sans-serif"

    @classmethod
    def apply_theme(cls):
        st.markdown(_CSS, unsafe_allow_html=True)

    @classmethod
    def create_logo_header(cls):
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:4px;
                        padding:12px 0;border-bottom:1px solid {BORDER};">
                <span style="font-size:2rem;color:{ACCENT};">⚓</span>
                <div>
                    <div style="font-size:1.6rem;font-weight:700;color:{DARK};line-height:1.1;
                                letter-spacing:-0.02em;">
                        AnchorAlpha
                    </div>
                    <div style="font-size:0.82rem;color:{MUTED};letter-spacing:0.04em;">
                        INSTITUTIONAL-GRADE MOMENTUM SCREENER
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    @classmethod
    def create_metric_card(cls, label: str, value: str, delta: str = None):
        delta_html = ""
        if delta:
            color = GREEN if delta.startswith("+") else RED
            delta_html = f'<div style="color:{color};font-size:0.85rem;margin-top:2px;">{delta}</div>'
        st.markdown(
            f"""
            <div class="aa-metric-card">
                <div class="aa-metric-label">{label}</div>
                <div class="aa-metric-value">{value}</div>
                {delta_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    @classmethod
    def format_momentum_display(cls, momentum_value: float) -> str:
        pct = momentum_value * 100
        if pct > 0:
            return f'<span style="color:{GREEN};font-weight:600;">+{pct:.2f}%</span>'
        elif pct < 0:
            return f'<span style="color:{RED};font-weight:600;">{pct:.2f}%</span>'
        return f'<span style="color:{MUTED};">0.00%</span>'

    @classmethod
    def create_tier_badge(cls, tier_key: str) -> str:
        tier_map = {
            "100B_200B": ("$100B–$200B", "#0d47a1"),
            "200B_500B": ("$200B–$500B", "#1565c0"),
            "500B_1T":   ("$500B–$1T",   "#1976d2"),
            "1T_plus":   ("$1T+",        "#0050a0"),
        }
        name, color = tier_map.get(tier_key, (tier_key, BLUE))
        return (
            f'<span style="background:{color};color:#fff;padding:2px 8px;'
            f'border-radius:4px;font-size:0.75rem;font-weight:600;">{name}</span>'
        )

    @classmethod
    def create_info_box(cls, content: str, box_type: str = "info"):
        colors = {"info": BLUE, "warning": ORANGE, "error": RED}
        color = colors.get(box_type, BLUE)
        st.markdown(
            f'<div style="border-left:4px solid {color};background:{BG_ALT};'
            f'padding:12px 16px;border-radius:4px;margin:8px 0;color:{BODY};">'
            f"{content}</div>",
            unsafe_allow_html=True,
        )

    @classmethod
    def create_stock_summary_card(cls, stock: Dict[str, Any]):
        ticker   = stock.get("ticker", "")
        company  = stock.get("company_name", "")
        price    = stock.get("price_display", "")
        mktcap   = stock.get("market_cap_display", "")
        summary  = stock.get("ai_summary", "")
        mom_html = cls.format_momentum_display(stock.get("momentum_value", 0))
        summary_html = (
            f'<div style="margin-top:8px;font-size:0.85rem;color:{MUTED};'
            f'font-style:italic;line-height:1.4;">{summary}</div>'
            if summary else ""
        )
        st.markdown(
            f"""
            <div class="aa-stock-card">
                <span style="font-size:1.05rem;font-weight:700;color:{BLUE};">{ticker}</span>
                <span style="color:{MUTED};font-size:0.85rem;margin-left:8px;">{company}</span>
                <div style="margin-top:6px;font-size:0.9rem;color:{BODY};">
                    <b>Price:</b> {price} &nbsp;|&nbsp;
                    <b>Mkt Cap:</b> {mktcap} &nbsp;|&nbsp;
                    <b>Momentum:</b> {mom_html}
                </div>
                {summary_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    @classmethod
    def create_footer(cls):
        st.markdown(
            f'<div style="text-align:center;color:{MUTED};font-size:0.8rem;'
            f'margin-top:32px;padding-top:16px;border-top:1px solid {BORDER};">'
            f"AnchorAlpha © 2026 &nbsp;·&nbsp; Powered by Financial Modeling Prep</div>",
            unsafe_allow_html=True,
        )


# ── CSS ────────────────────────────────────────────────────────────────────────

_CSS = f"""
<style>
/* ── Reset / base ── */
.stApp, .stApp > div, [data-testid="stAppViewContainer"] {{
    background-color: {BG} !important;
    color: {BODY};
    font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
}}

/* ── Hide default Streamlit branding ── */
#MainMenu, footer, header {{visibility: hidden;}}

/* ── Main block container ── */
.block-container {{
    background-color: {BG} !important;
    padding-top: 1.5rem;
}}

/* ── Top navigation tabs ── */
.stTabs [data-baseweb="tab-list"] {{
    background-color: {BG_ALT};
    border-bottom: 1px solid {BORDER};
    gap: 0;
    padding: 0 8px;
}}
.stTabs [data-baseweb="tab"] {{
    color: {MUTED};
    font-weight: 500;
    font-size: 0.95rem;
    padding: 12px 22px;
    border-bottom: 2px solid transparent;
    margin-bottom: -1px;
    background: transparent;
}}
.stTabs [aria-selected="true"] {{
    color: {ACCENT};
    border-bottom: 2px solid {ACCENT};
    font-weight: 700;
    background: transparent;
}}
.stTabs [data-baseweb="tab-panel"] {{
    background-color: {BG} !important;
    padding-top: 16px;
}}

/* ── Headers ── */
h1 {{ font-size:1.8rem; font-weight:700; color:{DARK}; margin-bottom:4px; }}
h2 {{ font-size:1.3rem; font-weight:600; color:{DARK}; }}
h3 {{ font-size:1.1rem; font-weight:600; color:{DARK}; }}
h4, h5, h6 {{ color:{DARK}; font-weight:600; }}
p, li {{ color: {BODY}; }}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background-color: {BG_ALT} !important;
    border-right: 1px solid {BORDER};
}}
[data-testid="stSidebar"] * {{ color: {BODY} !important; }}
[data-testid="stSidebarContent"] {{ background-color: {BG_ALT} !important; }}

/* ── Selectbox / inputs ── */
.stSelectbox label, .stMultiSelect label, .stSlider label, .stCheckbox label {{
    color: {MUTED} !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}}
[data-baseweb="select"] > div {{
    background-color: {BG_ALT} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 6px !important;
    color: {BODY} !important;
}}
[data-baseweb="select"] span, [data-baseweb="select"] div {{
    color: {BODY} !important;
    background-color: transparent !important;
}}
[data-baseweb="popover"] ul {{
    background-color: {BG_CARD} !important;
    border: 1px solid {BORDER} !important;
}}
[data-baseweb="popover"] li {{
    color: {BODY} !important;
}}
[data-baseweb="popover"] li:hover {{
    background-color: {ACCENT_DIM} !important;
}}

/* ── Slider ── */
[data-testid="stSlider"] > div > div > div > div {{
    background-color: {ACCENT} !important;
}}

/* ── Buttons ── */
.stButton > button {{
    background-color: {ACCENT};
    color: #fff;
    border: none;
    border-radius: 6px;
    font-weight: 600;
    padding: 8px 18px;
    transition: background 0.15s;
}}
.stButton > button:hover {{
    background-color: #2563eb;
    color: #fff;
}}

/* ── Metrics ── */
[data-testid="stMetric"] {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 14px 18px;
}}
[data-testid="stMetricLabel"] p {{
    color: {MUTED} !important;
    font-size: 0.75rem !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 600;
}}
[data-testid="stMetricValue"] {{
    color: {DARK} !important;
    font-size: 1.5rem !important;
    font-weight: 700 !important;
}}
[data-testid="stMetricDelta"] {{ font-size: 0.85rem; }}

/* ── Dataframes / tables ── */
[data-testid="stDataFrame"] {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    overflow: hidden;
}}
.dataframe, .dataframe * {{
    background-color: {BG_ALT} !important;
    color: {BODY} !important;
}}
.dataframe th {{
    background-color: {BG_CARD} !important;
    color: {MUTED} !important;
    font-weight: 600 !important;
    font-size: 0.75rem !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-bottom: 1px solid {BORDER} !important;
    padding: 10px 12px !important;
}}
.dataframe td {{
    color: {BODY} !important;
    font-size: 0.88rem !important;
    padding: 8px 12px !important;
    border-bottom: 1px solid {BORDER} !important;
}}
.dataframe tr:hover td {{ background-color: {ACCENT_DIM} !important; }}

/* ── Expander ── */
[data-testid="stExpander"] {{
    border: 1px solid {BORDER} !important;
    border-radius: 8px !important;
    margin-bottom: 10px !important;
    background: {BG_ALT} !important;
}}
[data-testid="stExpander"] summary {{
    font-weight: 600 !important;
    color: {DARK} !important;
    padding: 12px 16px !important;
    background: {BG_ALT} !important;
    border-radius: 8px !important;
}}
[data-testid="stExpander"] summary:hover {{
    background: {BG_CARD} !important;
}}
[data-testid="stExpander"] > div > div {{
    background: {BG_ALT} !important;
    padding: 0 16px 12px 16px;
}}

/* ── Info / alert boxes ── */
[data-testid="stAlert"] {{
    border-radius: 8px;
    background-color: {BG_CARD} !important;
    border: 1px solid {BORDER};
    color: {BODY} !important;
}}
[data-testid="stAlert"] * {{ color: {BODY} !important; }}

/* ── Divider ── */
hr {{ border: none; border-top: 1px solid {BORDER}; margin: 16px 0; }}

/* ── Caption ── */
.stCaption, [data-testid="stCaptionContainer"] p {{
    color: {MUTED} !important;
    font-size: 0.8rem !important;
}}

/* ── Spinner ── */
.stSpinner > div {{ border-top-color: {ACCENT} !important; }}

/* ── Custom metric card ── */
.aa-metric-card {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 12px;
}}
.aa-metric-label {{
    color: {MUTED};
    font-size: 0.73rem;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    font-weight: 600;
}}
.aa-metric-value {{
    color: {DARK};
    font-size: 1.6rem;
    font-weight: 700;
    margin-top: 4px;
}}

/* ── Stock card ── */
.aa-stock-card {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 10px;
    transition: border-color 0.15s, box-shadow 0.15s;
}}
.aa-stock-card:hover {{
    border-color: {ACCENT};
    box-shadow: 0 0 0 1px {ACCENT};
}}

/* ── Positive / negative helpers ── */
.aa-pos {{ color: {GREEN} !important; font-weight: 600; }}
.aa-neg {{ color: {RED}   !important; font-weight: 600; }}

/* ── Mobile ── */
@media (max-width: 768px) {{
    h1 {{ font-size: 1.3rem; }}
    .aa-metric-value {{ font-size: 1.2rem; }}
}}
</style>
"""


def apply_custom_theme():
    AnchorAlphaTheme.apply_theme()


def create_loading_spinner(message: str = "Loading data..."):
    st.markdown(
        f'<div style="text-align:center;color:{BLUE};font-size:1rem;padding:16px;">⚓ {message}</div>',
        unsafe_allow_html=True,
    )
