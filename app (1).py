import streamlit as st
import requests
from requests.adapters import HTTPAdapter
import math
import urllib.parse
import numpy as np
from datetime import datetime, date
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(
    page_title="Apex Intelligence — Apple Design System",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Strips whitespace indentation so Streamlit does not render HTML as code blocks
def render_html(html_str: str):
    cleaned = "\n".join(line.strip() for line in html_str.strip().splitlines() if line.strip())
    st.markdown(cleaned, unsafe_allow_html=True)

@st.cache_resource
def get_http_session() -> requests.Session:
    session = requests.Session()
    adapter = HTTPAdapter(pool_connections=65, pool_maxsize=65, max_retries=2)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
        "Accept": "application/json, text/plain, */*"
    })
    return session

if "sportybet_ng_codes" not in st.session_state:
    st.session_state.sportybet_ng_codes = {
        "3_odds": "VFUBGJ",
        "5_odds": "C5JEQK",
        "10_odds": "B2WCRA",
        "20_odds": "KFG5BM"
    }

# =====================================================================
# 1. APPLE DESIGN SYSTEM (SF PRO DISPLAY + OLED #000000 + #161617)
# =====================================================================
render_html("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

    /* Apple OLED True Black Canvas */
    .stApp {
        background-color: #000000 !important;
        color: #f5f5f7 !important;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Icons", "Helvetica Neue", Helvetica, Arial, sans-serif !important;
        letter-spacing: -0.015em;
    }

    /* Apple Headings */
    h1, h2, h3, h4, h5, h6 {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif !important;
        color: #f5f5f7 !important;
        letter-spacing: -0.03em !important;
        font-weight: 700 !important;
    }

    /* Apple Navigation Bar Glass */
    .apple-nav {
        background: rgba(22, 22, 23, 0.8) !important;
        backdrop-filter: blur(20px) saturate(180%) !important;
        -webkit-backdrop-filter: blur(20px) saturate(180%) !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.12);
        padding: 14px 24px;
        border-radius: 18px;
        margin-bottom: 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    /* Apple Card Surfaces (#161617) */
    .apple-card {
        background: #161617 !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 20px !important;
        padding: 22px 24px !important;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4) !important;
        transition: transform 0.25s cubic-bezier(0.25, 1, 0.5, 1), border-color 0.25s ease !important;
    }
    .apple-card:hover {
        transform: scale(1.01) !important;
        border-color: rgba(255, 255, 255, 0.18) !important;
    }

    /* Apple Buttons */
    .apple-button {
        background: #0071e3 !important;
        color: #ffffff !important;
