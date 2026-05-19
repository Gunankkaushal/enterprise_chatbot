import os
import pickle
import faiss
from config import FAISS_DIR

def load_or_create_faiss_index(department_id: int, embedding_dimension: int):
    department_dir = os.path.join(FAISS_DIR, str(department_id))
    os.makedirs(department_dir, exist_ok=True)

    index_path = os.path.join(department_dir, "index.faiss")
    metadata_path = os.path.join(department_dir, "metadata.pkl")

    if os.path.exists(index_path):
        index = faiss.read_index(index_path)
    else:
        index = faiss.IndexFlatL2(embedding_dimension)

    if os.path.exists(metadata_path):
        with open(metadata_path, "rb") as f:
            metadata = pickle.load(f)
    else:
        metadata = []

    return index, metadata, index_path, metadata_path

def save_faiss_index(index, metadata, index_path, metadata_path):
    # Atomic writes reduce index corruption risk during larger ingestion jobs.
    index_tmp_path = f"{index_path}.tmp"
    metadata_tmp_path = f"{metadata_path}.tmp"

    faiss.write_index(index, index_tmp_path)
    with open(metadata_tmp_path, "wb") as f:
        pickle.dump(metadata, f)

    os.replace(index_tmp_path, index_path)
    os.replace(metadata_tmp_path, metadata_path)


def add_embeddings_with_metadata(index, metadata, embeddings, new_metadata, batch_size: int = 1000):
    """
    Batched ingestion path for better stability on larger uploads while
    preserving existing FAISS IndexFlatL2 behavior.
    """
    if len(new_metadata) != embeddings.shape[0]:
        raise ValueError("Metadata count must match embedding rows.")

    start = 0
    total = embeddings.shape[0]
    while start < total:
        end = min(start + batch_size, total)
        index.add(embeddings[start:end])
        metadata.extend(new_metadata[start:end])
        start = end
