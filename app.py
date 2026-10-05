import os
import subprocess
import sys

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

# The "🔄 Sync" button embedded in the dashboard header (see
# build_dashboard.py) navigates this outer page directly to ?sync=1 — it's
# same-origin with the dashboard's components.html iframe, so no message
# listener is needed here.
if st.query_params.get("sync") == "1":
    with st.spinner("Syncing from Strava/Garmin..."):
        result = subprocess.run(
            [sys.executable, "garmin_sync.py"],
            capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__))
        )
        if result.returncode == 0:
            st.cache_resource.clear()
        else:
            st.error(f"Sync failed: {result.stderr}")
        st.query_params.clear()
        st.rerun()

@st.cache_resource(show_spinner="Building dashboard…")
def get_dashboard_html():
    """Generate the dashboard HTML from kite_data_clean.json.gz."""
    import build_dashboard
    return build_dashboard.build_html()

html = get_dashboard_html()
# height is an initial fallback; the embedded JS auto-resizes the iframe
# to fit actual content height once loaded (see build_dashboard.py).
components.html(html, height=3200, scrolling=True)
