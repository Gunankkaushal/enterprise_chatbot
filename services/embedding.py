import os
import numpy as np
from typing import List, Dict, Any

from sentence_transformers import SentenceTransformer
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode

import config

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

def get_text_nodes(processed_data: Dict[str, Any], file_name: str) -> List[TextNode]:
    doc_context = processed_data.get("doc_context", "")
    pages = processed_data.get("pages", [])

    if not pages and not doc_context:
        print("⚠️ Warning: No text to chunk. Returning empty list.")
        return []
    
    splitter = SentenceSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
    )

    nodes = []
    
    if doc_context.strip():
        context_chunks = splitter.split_text(doc_context)
        for i, chunk_text in enumerate(context_chunks):
            node = TextNode(
                text=chunk_text,
                metadata={
                    "file_name": os.path.basename(file_name),
                    "page_number": "Document Header", 
                    "chunk_number": i + 1
                }
            )
            nodes.append(node)

    for page in pages:
        page_num = page.get("page_number")
        page_text = page.get("text", "")
        
        if not page_text.strip():
            continue
            
        page_chunks = splitter.split_text(page_text)
        for i, chunk_text in enumerate(page_chunks):
            node = TextNode(
                text=chunk_text,
                metadata={
                    "file_name": os.path.basename(file_name),
                    "page_number": page_num,
                    "chunk_number": i + 1
                }
            )
            nodes.append(node)
    
    return nodes

def generate_embeddings(texts: List[str]) -> np.ndarray:
    embeddings = embedding_model.encode(texts)
    return np.array(embeddings, dtype=np.float32)