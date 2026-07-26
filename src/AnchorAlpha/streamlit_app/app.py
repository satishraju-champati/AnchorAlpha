"""
AnchorAlpha — unified 3-tab Streamlit entry point.
"""

import streamlit as st

st.set_page_config(
    page_title="AnchorAlpha",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="expanded",
)

try:
    from AnchorAlpha.streamlit_app.momentum_dashboard import render as render_momentum
    from AnchorAlpha.streamlit_app.research_dashboard import render as render_research
except ImportError:
    from momentum_dashboard import render as render_momentum
    from research_dashboard import render as render_research

tab1, tab2, tab3 = st.tabs(["📈 Momentum", "🔬 Research", "🚀 Live"])

with tab1:
    render_momentum()

with tab2:
    render_research()

with tab3:
    st.markdown("### 🚀 Live Trading")
    st.info("Live trading tab coming soon. Paper trading results from the Research tab will guide threshold selection before going live.")
