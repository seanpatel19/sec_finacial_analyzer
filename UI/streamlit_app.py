"""
Streamlit web interface for SEC Financial Analyzer
"""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.append(str(Path(__file__).parent.parent))

from main import SECAnalyzer

def main():
    st.set_page_