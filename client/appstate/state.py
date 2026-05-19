import streamlit as st


DEFAULT_STATE = {
    "is_authenticated": False,
    "access_token": "",
    "user_email": "",
    "is_admin": False,
    "department_id": None,
    "chat_history": [],
    "admin_chat_history": [],
}


def init_state() -> None:
    for key, value in DEFAULT_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = value


def logout() -> None:
    for key, value in DEFAULT_STATE.items():
        st.session_state[key] = value
