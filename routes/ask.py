from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional, Union

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
    department_id: Optional[int] = None

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
    # 1. Determine which indexes to search based on role and request
    indexes_to_search: List[Union[int, str]] = []
    department_name = "Multiple/Global"

    if current_user.is_admin:
        if request.department_id:
            # Admin targets a specific department (+ public context)
            department = db.query(Department).filter(Department.id == request.department_id).first()
            if not department:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found.")
            indexes_to_search = [request.department_id, "public"]
            department_name = department.name
        else:
            # Admin searches everything
            indexes_to_search = ["global"]
    else:
        # Regular user must query their own department + public
        if request.department_id and request.department_id != current_user.department_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access restricted.")
        
        indexes_to_search = ["public"]
        if current_user.department_id:
            indexes_to_search.append(current_user.department_id)
            department = db.query(Department).filter(Department.id == current_user.department_id).first()
            if department:
                department_name = department.name

    # 2. Check Cache
    # Updated build_cache_key to accept a stringified list of indexes instead of just department_id
    cache_key = build_cache_key(
        query=request.query,
        target_indexes=str(indexes_to_search) 
    )
    cached_response = get_cached_answer(cache_key)
    if cached_response:
        return AskResponse(**cached_response)
    
    # 3. Retrieve chunks from the targeted index(es)
    # Note: retrieve_top_k_chunks needs to be updated to accept a list of indexes
    nodes = retrieve_top_k_chunks(
        query=request.query,
        target_indexes=indexes_to_search, 
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

    # 4. Query LLM
    llm_response = query_llm_with_context(
        user_query=request.query,
        context_nodes=nodes,
        department_name=department_name
    )

    if llm_response.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=llm_response.get("answer")
        )

    # 5. Extract Sources
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

    # 6. Set Cache
    set_cached_answer(
        cache_key=cache_key,
        payload=response_payload.model_dump(),
        ttl_seconds=config.CACHE_TTL_SECONDS
    )

    return response_payload