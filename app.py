import streamlit as st
import streamlit.components.v1 as components
import subprocess
import os

st.set_page_config(
    page_title="Kite Dashboard — Aksel",
    page_icon="🪁",
    layout="wide",
)

# Hide Streamlit's default chrome for a fullscreen dashboard feel
st.markdown("""
<style>
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0 !important; max-width: 100% !important; }
iframe { display: block; }
</style>
""", unsafe_allow_html=True)

HTML_FILE = "kite_dashboard.html"

@st.cache_resource(show_spinner="Building dashboard…")
def build_html():
    """Generate the dashboard HTML from kite_data_clean.json."""
    subprocess.run(["python", "build_dashboard.py"], check=True)
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        return f.read()

html = build_html()
components.html(html, height=3200, scrolling=True)
