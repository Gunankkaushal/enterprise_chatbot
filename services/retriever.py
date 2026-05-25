import os
import faiss
import pickle
from typing import List, Union
from sqlalchemy.orm import Session

from llama_index.core.schema import TextNode

import config
from services.embedding import generate_embeddings
from .database.models import Department

def retrieve_top_k_chunks(query: str, target_indexes: List[Union[int, str]], db: Session, top_k: int = 5) -> List[TextNode]:
    print(f"\n🔍 Retrieving context for query: '{query}' across indexes: {target_indexes}...\n")
    
    # 1. Generate the query embedding once
    try:
        query_embedding = generate_embeddings([query])
    except Exception as e:
        print(f"Error generating query embedding: {e}")
        return []

    all_results = [] # Will store tuples of (distance, metadata_dict)
    
    # 2. Iterate through each target index and search
    for idx_identifier in target_indexes:
        index_dir = os.path.join(config.FAISS_DIR, str(idx_identifier))
        index_path = os.path.join(index_dir, "index.faiss")
        metadata_path = os.path.join(index_dir, "metadata.pkl")

        if not os.path.exists(index_path) or not os.path.exists(metadata_path):
            print(f"Warning: Index missing or incomplete for '{idx_identifier}'. Skipping.")
            continue

        try:
            index = faiss.read_index(index_path)
            with open(metadata_path, "rb") as f:
                metadata = pickle.load(f)
        except Exception as e:
            print(f"Error loading vector store for '{idx_identifier}': {e}")
            continue

        # Skip if the index is empty
        if index.ntotal == 0:
            continue

        # We pull top_k from *each* index to ensure we don't miss cross-index top matches
        search_k = min(top_k * 2, index.ntotal)
        distances, indices = index.search(query_embedding, search_k)
        
        # Accumulate valid results
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx < len(metadata):
                chunk_data = metadata[idx]
                distance = float(distances[0][i])
                all_results.append((distance, chunk_data))

    # 3. Sort merged results by distance
    # FAISS IndexFlatL2 uses L2 distance, so a lower score means higher similarity
    all_results.sort(key=lambda x: x[0])

    # 4. Extract top_k nodes
    retrieved_nodes = []
    for distance, chunk_data in all_results:
        if len(retrieved_nodes) >= top_k:
            break
            
        node_text = chunk_data.get("text", "")
        
        chunk_metadata = chunk_data.copy()
        chunk_metadata["distance_score"] = distance
        
        node = TextNode(
            text=node_text,
            metadata=chunk_metadata
        )
        retrieved_nodes.append(node)

    print(f"✅ Retrieval complete. Selected top {len(retrieved_nodes)} nodes across all targeted indexes.\n")
    return retrieved_nodes