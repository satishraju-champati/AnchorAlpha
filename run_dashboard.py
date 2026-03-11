#!/usr/bin/env python3
"""
Entry point for running the AnchorAlpha momentum dashboard.
This script sets up the proper Python path and runs the Streamlit app.
"""

import sys
import os
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Now we can import and run the dashboard
if __name__ == "__main__":
    import streamlit.web.cli as stcli
    
    # Set the dashboard file path
    dashboard_path = src_path / "AnchorAlpha" / "streamlit_app" / "momentum_dashboard.py"
    
    # Run streamlit with the dashboard
    sys.argv = [
        "streamlit",
        "run",
        str(dashboard_path),
        "--server.port=8503",
        "--server.headless=true"
    ]
    
    stcli.main()