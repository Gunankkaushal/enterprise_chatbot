import sys
from pathlib import Path

import streamlit as st

# Ensure project root is first in import resolution so backend modules
# like `services.database.*` are imported from the backend package.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from client.ui.admin_workspace import render_admin_workspace
from client.ui.auth import render_login
from client.ui.user_workspace import render_user_workspace
from client.appstate.state import init_state, logout
from client.appsvc.system_status import get_system_status

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
APP_ICON_PATH = ASSETS_DIR / "navikenz_icon.svg"

st.set_page_config(
    page_title="Enterprise Knowledge Chatbot",
    page_icon=str(APP_ICON_PATH),
    layout="wide"
)

st.markdown(
    """
    <style>
    :root {
        --brand:#1F4F64;
        --brand2:#2D6278;
        --accent:#8A2422;
        --accent-soft:#A83A36;
        --bg:#F2F5F8;
        --bg2:#E8EEF3;
        --text:#15202B;
        --muted:#5F6B76;
    }
    .stApp {background: linear-gradient(180deg, var(--bg) 0%, var(--bg2) 58%, #E0E8EF 100%);}
    h1, h2, h3 {color: var(--text);}
    .main-title {
        background: linear-gradient(90deg, var(--brand), var(--accent-soft));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        letter-spacing: .2px;
    }
    .brand-card {
        background: white;
        border: 1px solid #D4DEE8;
        border-radius: 16px;
        padding: 1rem 1.1rem;
        box-shadow: 0 10px 24px rgba(31, 79, 100, 0.14);
        margin-bottom: 0.9rem;
    }
    .sub-card {
        background: linear-gradient(180deg, #FFFFFF 0%, #FAFCFF 100%);
        border: 1px solid #D7E1EA;
        border-radius: 12px;
        padding: .65rem .8rem;
        margin: .35rem 0;
    }
    .role-chip {
        display:inline-block;
        background:#E7EFF3;
        color:var(--brand);
        border:1px solid #C5D4DE;
        padding:0.15rem 0.55rem;
        border-radius:999px;
        font-size:0.78rem;
        font-weight:600;
    }
    .status-up {
        color:#0F7A4A;
        background:#E8F8F0;
        border:1px solid #BFEBD4;
        border-radius:10px;
        padding:.25rem .45rem;
        font-size:.78rem;
        font-weight:600;
        display:inline-block;
    }
    .status-down {
        color:var(--accent);
        background:#FCEFED;
        border:1px solid #F0C2BC;
        border-radius:10px;
        padding:.25rem .45rem;
        font-size:.78rem;
        font-weight:600;
        display:inline-block;
    }
    .brand-row {
        display:flex;
        align-items:center;
        gap:.65rem;
    }
    .brand-logo {
        width:34px;
        height:34px;
        border-radius:8px;
        border:1px solid #D2DEE8;
        background:#F8FBFD;
        padding:3px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

init_state()

with st.sidebar:
    st.markdown(
        f"<div class='brand-card'><div class='brand-row'><img class='brand-logo' src='data:image/svg+xml;utf8,{APP_ICON_PATH.read_text(encoding='utf-8').replace('#', '%23').replace(chr(10), '')}' /><h3 style='margin:0' class='main-title'>NAVIKENZ KB</h3></div></div>",
        unsafe_allow_html=True
    )
    status = get_system_status()
    backend_class = "status-up" if status["backend"] == "up" else "status-down"
    redis_class = "status-up" if status["redis"] == "up" else "status-down"
    st.markdown("<div class='sub-card'><b>System Health</b></div>", unsafe_allow_html=True)
    st.markdown(f"<span class='{backend_class}'>Backend: {status['backend'].upper()}</span>", unsafe_allow_html=True)
    st.markdown(f"<span class='{redis_class}'>Redis Cache: {status['redis'].upper()}</span>", unsafe_allow_html=True)

    if st.session_state["is_authenticated"]:
        role = "Admin" if st.session_state["is_admin"] else "User"
        st.markdown(f"<span class='role-chip'>{role}</span>", unsafe_allow_html=True)
        st.write(f"Email: {st.session_state['user_email']}")
        if st.button("Logout", use_container_width=True):
            logout()
            st.rerun()
    else:
        st.write("Please log in.")

if not st.session_state["is_authenticated"]:
    render_login()
else:
    if st.session_state["is_admin"]:
        render_admin_workspace()
    else:
        render_user_workspace()
