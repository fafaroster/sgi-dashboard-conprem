"""
Futuristic CSS injection module for the SGI Audit Dashboard.

Injects a comprehensive "year 2100" premium visual experience using
glassmorphism, neon glow effects, animated gradients, and custom typography.

This module does NOT alter data logic or component structure. It only
applies visual styling via CSS injection through st.markdown(unsafe_allow_html=True).
"""

from __future__ import annotations

import streamlit as st


def inject_futuristic_css() -> None:
    """Inject comprehensive futuristic CSS into the Streamlit app.

    Must be called immediately after st.set_page_config() in app.py.
    Applies glassmorphism panels, animated gradient background, neon glow
    effects, custom fonts, enhanced metric cards, styled buttons, gradient
    dividers, custom scrollbars, and glassmorphism DataFrames.
    """
    st.markdown(_FUTURISTIC_CSS, unsafe_allow_html=True)


_FUTURISTIC_CSS = """
<style>
/* ==========================================================================
   A. CUSTOM FONTS — Space Grotesk for headers, Inter for body
   ========================================================================== */

@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}

h1, h2, h3, h4 {
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600;
    letter-spacing: -0.02em;
}

/* ==========================================================================
   B. ANIMATED GRADIENT BACKGROUND — Cyberpunk dark with slow-moving gradient
   ========================================================================== */

.stApp {
    background: linear-gradient(-45deg, #0a0a1a, #1a0a2e, #0a1628, #0d1117, #1a0520);
    background-size: 400% 400%;
    animation: gradientShift 15s ease infinite;
}

@keyframes gradientShift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

/* ==========================================================================
   C. GLASSMORPHISM PANELS — Expanders, metrics, containers
   ========================================================================== */

[data-testid="stExpander"],
[data-testid="stMetric"],
div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] > div[data-testid="column"] > div[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(15, 23, 42, 0.6) !important;
    backdrop-filter: blur(20px) !important;
    -webkit-backdrop-filter: blur(20px) !important;
    border: 1px solid rgba(99, 102, 241, 0.3) !important;
    border-radius: 16px !important;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
}

/* Sidebar glassmorphism */
[data-testid="stSidebar"] > div:first-child {
    background: rgba(15, 23, 42, 0.8) !important;
    backdrop-filter: blur(20px) !important;
    -webkit-backdrop-filter: blur(20px) !important;
}

/* ==========================================================================
   D. NEON / GLOW EFFECTS — Headers, metrics, sidebar
   ========================================================================== */

h1, h2, h3 {
    text-shadow: 0 0 10px rgba(99, 102, 241, 0.5), 0 0 20px rgba(99, 102, 241, 0.3);
}

[data-testid="stMetricValue"] {
    text-shadow: 0 0 8px rgba(34, 211, 238, 0.6) !important;
    color: #22d3ee !important;
}

[data-testid="stSidebar"] {
    border-right: 1px solid rgba(99, 102, 241, 0.4) !important;
    box-shadow: 4px 0 20px rgba(99, 102, 241, 0.1) !important;
}

/* ==========================================================================
   E. METRIC CARDS ENHANCEMENT — Hover effects, transitions
   ========================================================================== */

[data-testid="stMetric"] {
    background: rgba(15, 23, 42, 0.7) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid rgba(99, 102, 241, 0.25) !important;
    border-radius: 12px !important;
    padding: 1rem !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

[data-testid="stMetric"]:hover {
    border-color: rgba(99, 102, 241, 0.6) !important;
    box-shadow: 0 0 20px rgba(99, 102, 241, 0.15) !important;
    transform: translateY(-2px) !important;
}

/* ==========================================================================
   F. BUTTONS & INTERACTIVES — Gradient backgrounds, glow hover
   ========================================================================== */

.stButton > button {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(168, 85, 247, 0.2)) !important;
    border: 1px solid rgba(99, 102, 241, 0.5) !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
    transition: all 0.3s ease !important;
    text-shadow: 0 0 5px rgba(99, 102, 241, 0.3);
}

.stButton > button:hover {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.4), rgba(168, 85, 247, 0.4)) !important;
    border-color: rgba(99, 102, 241, 0.8) !important;
    box-shadow: 0 0 25px rgba(99, 102, 241, 0.3) !important;
    transform: scale(1.02) !important;
}

/* ==========================================================================
   G. DIVIDERS WITH GRADIENT
   ========================================================================== */

hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.5), rgba(168, 85, 247, 0.5), transparent) !important;
}

/* ==========================================================================
   H. SCROLLBAR STYLING
   ========================================================================== */

::-webkit-scrollbar {
    width: 6px;
}

::-webkit-scrollbar-track {
    background: rgba(15, 23, 42, 0.3);
}

::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, #6366f1, #a855f7);
    border-radius: 3px;
}

/* ==========================================================================
   I. DATAFRAMES WITH GLASSMORPHISM
   ========================================================================== */

[data-testid="stDataFrame"] {
    background: rgba(15, 23, 42, 0.5) !important;
    backdrop-filter: blur(10px) !important;
    border: 1px solid rgba(99, 102, 241, 0.2) !important;
    border-radius: 12px !important;
    overflow: hidden !important;
}

/* ==========================================================================
   ADDITIONAL POLISH — Selectboxes, inputs, tabs
   ========================================================================== */

/* Selectbox / Multiselect / Input styling */
[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div,
.stTextInput > div > div > input {
    background: rgba(15, 23, 42, 0.6) !important;
    border: 1px solid rgba(99, 102, 241, 0.3) !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
}

/* Tabs styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}

.stTabs [data-baseweb="tab"] {
    background: rgba(15, 23, 42, 0.5) !important;
    border: 1px solid rgba(99, 102, 241, 0.2) !important;
    border-radius: 8px 8px 0 0 !important;
    color: #e2e8f0 !important;
}

.stTabs [aria-selected="true"] {
    background: rgba(99, 102, 241, 0.2) !important;
    border-color: rgba(99, 102, 241, 0.5) !important;
}

/* Download button styling */
.stDownloadButton > button {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(34, 211, 238, 0.2)) !important;
    border: 1px solid rgba(16, 185, 129, 0.5) !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
    transition: all 0.3s ease !important;
}

.stDownloadButton > button:hover {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.4), rgba(34, 211, 238, 0.4)) !important;
    border-color: rgba(16, 185, 129, 0.8) !important;
    box-shadow: 0 0 25px rgba(16, 185, 129, 0.3) !important;
    transform: scale(1.02) !important;
}

/* Info/Warning/Error boxes with glassmorphism */
[data-testid="stAlert"] {
    background: rgba(15, 23, 42, 0.6) !important;
    backdrop-filter: blur(10px) !important;
    border: 1px solid rgba(99, 102, 241, 0.2) !important;
    border-radius: 12px !important;
}

/* Plotly chart containers */
[data-testid="stPlotlyChart"] {
    background: rgba(15, 23, 42, 0.4) !important;
    backdrop-filter: blur(10px) !important;
    border: 1px solid rgba(99, 102, 241, 0.15) !important;
    border-radius: 12px !important;
    padding: 0.5rem !important;
}

/* Main header area glow enhancement */
[data-testid="stHeader"] {
    background: rgba(10, 10, 26, 0.8) !important;
    backdrop-filter: blur(10px) !important;
}

/* Metric delta styling */
[data-testid="stMetricDelta"] {
    color: #22d3ee !important;
}

</style>
"""
