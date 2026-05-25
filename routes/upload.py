import os
import uuid
from typing import Optional

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
async def upload_document(
    file: UploadFile = File(...), 
    department_id: Optional[int] = Form(None), # Made optional for Public docs
    db: Session = Depends(get_db), 
    admin_user: User = Depends(require_admin)
):
    # 1. Determine the target index and validate department
    department_name = "Public"
    index_identifier = "public"
    
    if department_id is not None:
        department = db.query(Department).filter(Department.id == department_id).first()
        if not department:
            raise HTTPException(status_code=404, detail="Department not found")
        department_name = department.name
        index_identifier = department.id

    # 2. File validation and saving
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

    # 3. Document processing
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

    # 4. Prepare Metadata
    new_metadata = []
    for node in nodes:
        new_metadata.append({
            "text": node.text,
            "source": node.metadata.get("file_name"),
            "department_id": department_id, # Will be None for public docs
            "file_hash": file_hash,
            "page_number": node.metadata.get("page_number"),
            "chunk_number": node.metadata.get("chunk_number")
        })

    # 5. Update Specific Index (Either "public" or the department ID)
    target_index, target_metadata, target_idx_path, target_meta_path = load_or_create_faiss_index(
        index_identifier, 
        embedding_dimension
    )
    add_embeddings_with_metadata(target_index, target_metadata, embeddings, new_metadata)
    save_faiss_index(target_index, target_metadata, target_idx_path, target_meta_path)

    # 6. Update Global Index (Every document goes here)
    global_index, global_metadata, global_idx_path, global_meta_path = load_or_create_faiss_index(
        "global", 
        embedding_dimension
    )
    add_embeddings_with_metadata(global_index, global_metadata, embeddings, new_metadata)
    save_faiss_index(global_index, global_metadata, global_idx_path, global_meta_path)

    # 7. Database Persistence
    new_document = Document(
        filename=file.filename,
        filepath=file_path,
        file_hash=file_hash,
        uploaded_by=admin_user.id,
        department_id=department_id # Will be null in DB if public
    )
    db.add(new_document)
    db.commit()
    db.refresh(new_document)

    return {
        "message": "Document uploaded successfully",
        "document_id": new_document.id,
        "department": department_name,
        "indexes_updated": [str(index_identifier), "global"],
        "chunks_indexed": len(nodes)
    }