from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from services.database.db_connection import get_db
from .auth import get_current_user
from services.database.models import Department, User
from services.retriever import retrieve_top_k_chunks
from services.llm import query_llm_with_context
from services.cache import build_cache_key, get_cached_answer, set_cached_answer

import config

askrouter = APIRouter(
    prefix="/ask",
    tags=["Ask Questions"]
)

class AskRequest(BaseModel):
    query: str
    department_id: int

class SourceMetadata(BaseModel):
    source: str
    page_number: Optional[str] = None
    distance_score: Optional[float] = None

class AskResponse(BaseModel):
    answer: str
    status: str
    clarifying_questions: List[str] = []
    sources: List[SourceMetadata] = []

@askrouter.post("/", response_model=AskResponse)
async def ask_question(request: AskRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    department = db.query(Department).filter(Department.id == request.department_id).first()
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Department not found."
        )
    
    if current_user.department_id != request.department_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Access restricted."
        )

    cache_key = build_cache_key(
        query=request.query,
        department_id=request.department_id
    )
    cached_response = get_cached_answer(cache_key)
    if cached_response:
        return AskResponse(**cached_response)
    
    nodes = retrieve_top_k_chunks(
        query=request.query,
        department_id=request.department_id,
        db=db,
        top_k=config.TOP_K_CHUNKS
    )

    if not nodes:
        return AskResponse(
            answer="I'm sorry, I couldn't find any relevant documents to answer your question. Please ensure documents have been uploaded for this department.",
            status="insufficient",
            clarifying_questions=[],
            sources=[]
        )

    llm_response = query_llm_with_context(
        user_query=request.query,
        context_nodes=nodes,
        department_name=department.name
    )

    if llm_response.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=llm_response.get("answer")
        )

    unique_sources = {}
    for node in nodes:
        source_name = node.metadata.get("source", "Unknown Document")
        page_num = str(node.metadata.get("page_number", "N/A"))
        
        doc_key = f"{source_name}_page_{page_num}"
        
        if doc_key not in unique_sources:
            unique_sources[doc_key] = SourceMetadata(
                source=source_name,
                page_number=page_num,
                distance_score=round(node.metadata.get("distance_score", 0.0), 4)
            )

    sources_list = list(unique_sources.values())

    response_payload = AskResponse(
        answer=llm_response.get("answer", ""),
        status=llm_response.get("status", "sufficient"),
        clarifying_questions=llm_response.get("questions", []),
        sources=sources_list
    )

    set_cached_answer(
        cache_key=cache_key,
        payload=response_payload.model_dump(),
        ttl_seconds=config.CACHE_TTL_SECONDS
    )

    return response_payload
