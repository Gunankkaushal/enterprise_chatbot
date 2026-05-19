import streamlit as st
from requests import HTTPError

from client.appsvc.admin_ops import (
    delete_document,
    delete_user,
    get_dashboard_stats,
    list_departments,
    list_documents,
    list_users,
    reindex_department,
)
from client.appsvc.api_client import ask_question, create_department, register_user, upload_document


def _tab_dashboard() -> None:
    st.subheader("Platform Snapshot")
    stats = get_dashboard_stats()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Departments", stats["departments"])
    c2.metric("Users", stats["users"])
    c3.metric("Admins", stats["admins"])
    c4.metric("Documents", stats["documents"])


def _tab_upload() -> None:
    st.subheader("Upload PDF/DOCX")
    st.caption("Upload enterprise documents into a selected department knowledge base.")
    departments = list_departments()
    if not departments:
        st.warning("No departments found. Create one first.")
        return
    department_map = {f"{d.id} - {d.name}": d.id for d in departments}
    selected = st.selectbox("Department", list(department_map.keys()))
    file = st.file_uploader("Select file", type=["pdf", "docx"])
    if st.button("Upload Document", use_container_width=True):
        if file is None:
            st.error("Please select a file.")
            return
        dep_id = department_map[selected]
        try:
            response = upload_document(
                token=st.session_state["access_token"],
                department_id=dep_id,
                file_name=file.name,
                file_bytes=file.getvalue()
            )
            st.success(f"Uploaded. Chunks indexed: {response.get('chunks_indexed')}")
        except HTTPError as exc:
            try:
                detail = exc.response.json().get("detail", str(exc))
            except Exception:
                detail = str(exc)
            st.error(f"Upload failed: {detail}")
        except Exception as exc:
            st.error(f"Upload failed: {exc}")


def _tab_reindex() -> None:
    st.subheader("Reindex Department")
    st.caption("Rebuild embeddings and FAISS index from current uploaded documents.")
    departments = list_departments()
    if not departments:
        st.warning("No departments available.")
        return
    department_map = {f"{d.id} - {d.name}": d.id for d in departments}
    selected = st.selectbox("Department to Reindex", list(department_map.keys()), key="reindex_dep")
    if st.button("Run Reindex", use_container_width=True):
        dep_id = department_map[selected]
        with st.spinner("Reindexing..."):
            result = reindex_department(dep_id)
        st.success(
            f"Reindex complete. Documents processed: {result['documents']}, "
            f"Chunks indexed: {result['chunks']}."
        )


def _tab_documents() -> None:
    st.subheader("Document Management")
    docs = list_documents()
    if not docs:
        st.info("No documents found.")
        return
    for doc in docs:
        c1, c2, c3, c4 = st.columns([3, 1, 2, 1])
        c1.write(f"{doc.filename}")
        c2.write(f"Dept: {doc.department_id}")
        c3.write(f"Doc ID: {doc.id}")
        if c4.button("Delete", key=f"del_doc_{doc.id}"):
            if delete_document(doc.id):
                st.success(f"Deleted document {doc.id}.")
                st.rerun()
            else:
                st.error("Delete failed.")


def _tab_users() -> None:
    st.subheader("User Management")
    with st.expander("Create User"):
        with st.form("create_user_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            is_admin = st.checkbox("Is Admin")
            departments = list_departments()
            dep_options = ["None"] + [f"{d.id} - {d.name}" for d in departments]
            dep_selected = st.selectbox("Department", dep_options)
            submitted = st.form_submit_button("Create User")
        if submitted:
            dep_id = None
            if dep_selected != "None":
                dep_id = int(dep_selected.split(" - ")[0])
            try:
                register_user(
                    email=email,
                    password=password,
                    is_admin=is_admin,
                    department_id=dep_id
                )
                st.success("User created.")
                st.rerun()
            except HTTPError as exc:
                try:
                    detail = exc.response.json().get("detail", str(exc))
                except Exception:
                    detail = str(exc)
                st.error(f"Create user failed: {detail}")
            except Exception as exc:
                st.error(f"Create user failed: {exc}")

    st.markdown("### Existing Users")
    users = list_users()
    for user in users:
        c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
        c1.write(user.email)
        c2.write("Admin" if user.is_admin else "User")
        c3.write(f"Dept: {user.department_id}")
        if c4.button("Delete", key=f"del_user_{user.id}"):
            if user.id == 1:
                st.warning("Skipping delete of primary seed/admin user id 1.")
            elif delete_user(user.id):
                st.success(f"Deleted user {user.id}.")
                st.rerun()
            else:
                st.error("Delete failed.")


def _render_sources(sources) -> None:
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


def _tab_admin_chatbot() -> None:
    st.subheader("Admin Chatbot")
    st.caption("Ask across any department by selecting department scope.")

    departments = list_departments()
    if not departments:
        st.warning("No departments found. Create/upload documents first.")
        return

    department_map = {f"{d.id} - {d.name}": d.id for d in departments}
    selected = st.selectbox("Department Scope", list(department_map.keys()), key="admin_chat_dep")
    selected_dep_id = department_map[selected]

    query = st.chat_input("Ask a question as admin", key="admin_chat_input")
    if query:
        st.session_state["admin_chat_history"].append({
            "role": "user",
            "message": f"[Dept {selected_dep_id}] {query}",
            "sources": []
        })
        try:
            response = ask_question(
                token=st.session_state["access_token"],
                query=query,
                department_id=int(selected_dep_id)
            )
            st.session_state["admin_chat_history"].append({
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

    for item in st.session_state["admin_chat_history"]:
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


def render_admin_workspace() -> None:
    header_left, header_right = st.columns([3, 2])
    header_left.markdown("<h1 class='main-title'>Admin Control Center</h1>", unsafe_allow_html=True)
    header_right.markdown(f"**Admin:** `{st.session_state['user_email']}`")
    st.markdown(
        "<div class='sub-card'>Manage departments, users, documents, indexing, and run cross-department admin chat.</div>",
        unsafe_allow_html=True
    )

    with st.expander("Create Department"):
        dept_name = st.text_input("Department Name")
        if st.button("Create Department"):
            if not dept_name.strip():
                st.error("Department name is required.")
            else:
                try:
                    response = create_department(
                        token=st.session_state["access_token"],
                        name=dept_name.strip()
                    )
                    st.success(
                        f"Created department: {response['department']['name']} "
                        f"(ID: {response['department']['id']})"
                    )
                except HTTPError as exc:
                    try:
                        detail = exc.response.json().get("detail", str(exc))
                    except Exception:
                        detail = str(exc)
                    st.error(f"Create department failed: {detail}")
                except Exception as exc:
                    st.error(f"Create department failed: {exc}")

    st.markdown("---")
    t1, t2, t3, t4, t5, t6 = st.tabs(
        ["Dashboard Stats", "PDF Upload", "Reindex", "Document Management", "User Management", "Admin Chatbot"]
    )
    with t1:
        _tab_dashboard()
    with t2:
        _tab_upload()
    with t3:
        _tab_reindex()
    with t4:
        _tab_documents()
    with t5:
        _tab_users()
    with t6:
        _tab_admin_chatbot()
