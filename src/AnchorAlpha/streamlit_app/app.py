"""
Main Streamlit application entry point for AnchorAlpha Momentum Screener.
"""

import sys
import os
import logging
from pathlib import Path

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import dashboard after path setup
from AnchorAlpha.src.AnchorAlpha.streamlit_app.momentum_dashboard import main

if __name__ == "__main__":
    main()