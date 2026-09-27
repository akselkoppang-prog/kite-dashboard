import streamlit as st
import streamlit.components.v1 as components

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

@st.cache_resource(show_spinner="Building dashboard…")
def get_dashboard_html():
    """Generate the dashboard HTML from kite_data_clean.json.gz."""
    import build_dashboard
    return build_dashboard.build_html()

html = get_dashboard_html()
# height is an initial fallback; the embedded JS auto-resizes the iframe
# to fit actual content height once loaded (see build_dashboard.py).
components.html(html, height=3200, scrolling=True)
