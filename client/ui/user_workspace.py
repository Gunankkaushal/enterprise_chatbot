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


def _user_history_key(user_email: str, department_id: int) -> str:
    return f"user:{user_email}:dept:{department_id}"


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

    history_store = st.session_state.setdefault("chat_history_by_user_dept", {})
    history_key = _user_history_key(st.session_state["user_email"], int(department_id))
    current_history = history_store.setdefault(history_key, [])

    if st.button("Clear Chat History", key="clear_user_chat_history"):
        history_store[history_key] = []
        st.rerun()

    query = st.chat_input("Ask about policies, processes, or documents in your department")
    if query:
        current_history.append({
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
            current_history.append({
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

    for item in current_history:
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
