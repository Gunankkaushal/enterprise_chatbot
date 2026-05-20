import streamlit as st
from requests import HTTPError

from client.appsvc.api_client import decode_token_claims, login


def render_login() -> None:
    left, right = st.columns([1.1, 1], gap="large")
    with left:
        st.markdown("<h1 class='main-title'>Enterprise Knowledge Assistant</h1>", unsafe_allow_html=True)
        st.write("Secure, department-scoped document intelligence for teams.")
        st.markdown(
            "<div class='sub-card'>Sign in to continue to your role-based workspace.</div>",
            unsafe_allow_html=True
        )

    with right:
        st.subheader("Login")
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)

    if not submitted:
        return

    if not email or not password:
        st.error("Email and password are required.")
        return

    try:
        data = login(email=email, password=password)
        token = data["access_token"]
        claims = decode_token_claims(token)
        st.session_state["is_authenticated"] = True
        st.session_state["access_token"] = token
        st.session_state["user_email"] = email
        st.session_state["is_admin"] = bool(claims.get("is_admin", False))
        st.session_state["department_id"] = claims.get("department_id")
        st.success("Login successful.")
        st.rerun()
    except HTTPError as exc:
        try:
            detail = exc.response.json().get("detail", str(exc))
        except Exception:
            detail = str(exc)
        st.error(f"Login failed: {detail}")
    except Exception as exc:
        st.error(f"Login failed: {exc}")
