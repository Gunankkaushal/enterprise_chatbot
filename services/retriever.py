import os
import faiss
import pickle
from typing import List
from sqlalchemy.orm import Session

from llama_index.core.schema import TextNode

import config
from services.embedding import generate_embeddings
from .database.models import Department

def retrieve_top_k_chunks(query: str, department_id: int, db: Session, top_k: int = 5) -> List[TextNode]:
    department = db.query(Department).filter(Department.id == department_id).first()
    
    if not department:
        print(f"Error: Department with ID {department_id} not found.")
        return []

    department_name = department.name
    print(f"\n🔍 Retrieving context for query: '{query}' in department '{department_name}' (ID: {department_id})...\n")
    
    department_dir = os.path.join(config.FAISS_DIR, str(department_id))
    index_path = os.path.join(department_dir, "index.faiss")
    metadata_path = os.path.join(department_dir, "metadata.pkl")

    if not os.path.exists(index_path) or not os.path.exists(metadata_path):
        print(f"Error: No index found for department '{department_name}'. Please upload documents first.")
        return []

    try:
        index = faiss.read_index(index_path)
        with open(metadata_path, "rb") as f:
            metadata = pickle.load(f)
    except Exception as e:
        print(f"Error loading vector store: {e}")
        return []

    query_embedding = generate_embeddings([query])

    search_k = top_k * 2 
    distances, indices = index.search(query_embedding, search_k)

    retrieved_nodes = []
    
    for i, idx in enumerate(indices[0]):
        if len(retrieved_nodes) >= top_k:
            break
            
        if idx != -1 and idx < len(metadata):
            chunk_data = metadata[idx]
            
            if chunk_data.get("department_id") != department_id:
                continue
            
            node_text = chunk_data.get("text", "")
            
            chunk_metadata = chunk_data.copy()
            chunk_metadata["distance_score"] = float(distances[0][i])
            
            node = TextNode(
                text=node_text,
                metadata=chunk_metadata
            )
            retrieved_nodes.append(node)

    print(f"✅ Retrieval complete. Selected top {len(retrieved_nodes)} nodes.\n")
    return retrieved_nodes
