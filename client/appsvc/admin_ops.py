import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Ensure backend project root is available for absolute imports.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config
from services.database.db_connection import SessionLocal
from services.database.models import Department, Document, User
from services.embedding import generate_embeddings, get_text_nodes
from services.vector_store import load_or_create_faiss_index, save_faiss_index
from utils.parsers import extract_and_clean_document


def get_dashboard_stats() -> Dict[str, int]:
    db = SessionLocal()
    try:
        return {
            "departments": db.query(Department).count(),
            "users": db.query(User).count(),
            "documents": db.query(Document).count(),
            "admins": db.query(User).filter(User.is_admin.is_(True)).count(),
        }
    finally:
        db.close()


def list_departments() -> List[Department]:
    db = SessionLocal()
    try:
        return db.query(Department).order_by(Department.id.asc()).all()
    finally:
        db.close()


def list_documents(department_id: Optional[int] = None) -> List[Document]:
    db = SessionLocal()
    try:
        query = db.query(Document)
        if department_id:
            query = query.filter(Document.department_id == department_id)
        return query.order_by(Document.created_at.desc()).all()
    finally:
        db.close()


def list_users() -> List[User]:
    db = SessionLocal()
    try:
        return db.query(User).order_by(User.id.asc()).all()
    finally:
        db.close()


def delete_document(document_id: int) -> bool:
    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return False
        file_path = document.filepath
        db.delete(document)
        db.commit()
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        return True
    finally:
        db.close()


def delete_user(user_id: int) -> bool:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        db.delete(user)
        db.commit()
        return True
    finally:
        db.close()


def reindex_department(department_id: int) -> Dict[str, int]:
    db = SessionLocal()
    try:
        documents = db.query(Document).filter(Document.department_id == department_id).all()
        department_dir = os.path.join(config.FAISS_DIR, str(department_id))
        if os.path.exists(department_dir):
            shutil.rmtree(department_dir)

        total_chunks = 0
        processed_docs = 0

        for document in documents:
            file_path = document.filepath
            extension = os.path.splitext(document.filename)[1].lower()
            if not os.path.exists(file_path):
                continue
            doc_data = extract_and_clean_document(file_path, extension)
            nodes = get_text_nodes(doc_data, document.filename)
            if not nodes:
                continue
            chunk_texts = [node.text for node in nodes]
            embeddings = generate_embeddings(chunk_texts)
            embedding_dimension = embeddings.shape[1]
            index, metadata, index_path, metadata_path = load_or_create_faiss_index(
                department_id,
                embedding_dimension
            )
            index.add(embeddings)
            for node in nodes:
                metadata.append({
                    "text": node.text,
                    "source": node.metadata.get("file_name"),
                    "department_id": department_id,
                    "file_hash": document.file_hash,
                    "page_number": node.metadata.get("page_number"),
                    "chunk_number": node.metadata.get("chunk_number")
                })
            save_faiss_index(index, metadata, index_path, metadata_path)
            total_chunks += len(nodes)
            processed_docs += 1

        return {"documents": processed_docs, "chunks": total_chunks}
    finally:
        db.close()
