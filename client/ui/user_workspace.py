import streamlit as st
from requests import HTTPError

from client.appsvc.api_client import ask_question


def _render_sources(sources):
    if not sources:
        return
    st.caption("Sources & Citations")
    for source in sources:
        src = source.get("source", "Unknown")
        page = source.get("page_number", "N/A")
        score = source.get("distance_score")
        if score is None:
            st.write(f"- {src} (Page: {page})")
        else:
            st.write(f"- {src} (Page: {page}, Score: {score})")


def render_user_workspace() -> None:
    c1, c2 = st.columns([3, 2])
    c1.markdown("<h1 class='main-title'>Employee Workspace</h1>", unsafe_allow_html=True)
    c2.markdown(
        f"**User:** `{st.session_state['user_email']}`  \n"
        f"**Department:** `{st.session_state.get('department_id')}`"
    )
    st.markdown(
        "<div class='sub-card'>Ask policy and process questions from your department knowledge base.</div>",
        unsafe_allow_html=True
    )

    department_id = st.session_state.get("department_id")
    if department_id is None:
        st.error("No department is mapped to this user.")
        return

    query = st.chat_input("Ask about policies, processes, or documents in your department")
    if query:
        st.session_state["chat_history"].append({
            "role": "user",
            "message": query,
            "sources": []
        })
        try:
            response = ask_question(
                token=st.session_state["access_token"],
                query=query,
                department_id=int(department_id)
            )
            st.session_state["chat_history"].append({
                "role": "assistant",
                "message": response.get("answer", ""),
                "status": response.get("status", ""),
                "clarifying_questions": response.get("clarifying_questions", []),
                "sources": response.get("sources", [])
            })
        except HTTPError as exc:
            try:
                detail = exc.response.json().get("detail", str(exc))
            except Exception:
                detail = str(exc)
            st.error(f"Ask failed: {detail}")
        except Exception as exc:
            st.error(f"Ask failed: {exc}")

    for item in st.session_state["chat_history"]:
        with st.chat_message(item["role"]):
            st.markdown(item["message"])
            if item["role"] == "assistant":
                if item.get("status"):
                    st.caption(f"Status: {item['status']}")
                if item.get("clarifying_questions"):
                    st.caption("Clarifying Questions")
                    for q in item["clarifying_questions"]:
                        st.write(f"- {q}")
                _render_sources(item.get("sources", []))
