import os
import uuid

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from services.database.db_connection import get_db
from services.database.models import User, Department, Document
from routes.auth import require_admin

from config import UPLOAD_DIR
from utils.helpers import calculate_file_hash
from utils.parsers import extract_and_clean_document
from services.embedding import get_text_nodes, generate_embeddings
from services.vector_store import (
    load_or_create_faiss_index,
    save_faiss_index,
    add_embeddings_with_metadata
)

uploadrouter = APIRouter(
    prefix="/upload",
    tags=["Upload Documents"]
)

ALLOWED_EXTENSIONS = {".pdf", ".docx"}

@uploadrouter.post("/")
async def upload_document(department_id: int = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db), admin_user: User = Depends(require_admin)):
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    extension = os.path.splitext(file.filename)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files supported.")

    file_bytes = await file.read()
    file_hash = calculate_file_hash(file_bytes)
    
    if db.query(Document).filter(Document.file_hash == file_hash).first():
        raise HTTPException(status_code=409, detail="Duplicate document detected.")

    unique_filename = f"{uuid.uuid4()}{extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    try:
        doc_data = extract_and_clean_document(file_path, extension)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    nodes = get_text_nodes(doc_data, file.filename)
    if not nodes:
        raise HTTPException(status_code=400, detail="No readable text found in document after cleaning.")

    chunk_texts = [node.text for node in nodes]
    embeddings = generate_embeddings(chunk_texts)
    embedding_dimension = embeddings.shape[1]

    index, metadata, index_path, metadata_path = load_or_create_faiss_index(
        department.id, 
        embedding_dimension
    )
    
    new_metadata = []
    for node in nodes:
        new_metadata.append({
            "text": node.text,
            "source": node.metadata.get("file_name"),
            "department_id": department.id,
            "file_hash": file_hash,
            "page_number": node.metadata.get("page_number"),
            "chunk_number": node.metadata.get("chunk_number")
        })

    add_embeddings_with_metadata(
        index=index,
        metadata=metadata,
        embeddings=embeddings,
        new_metadata=new_metadata
    )

    save_faiss_index(index, metadata, index_path, metadata_path)

    new_document = Document(
        filename=file.filename,
        filepath=file_path,
        file_hash=file_hash,
        uploaded_by=admin_user.id,
        department_id=department.id
    )
    db.add(new_document)
    db.commit()
    db.refresh(new_document)

    return {
        "message": "Document uploaded successfully",
        "document_id": new_document.id,
        "department": department.name,
        "chunks_indexed": len(nodes)
    }
