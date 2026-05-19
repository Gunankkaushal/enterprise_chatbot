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
    faiss.write_index(index, index_path)
    with open(metadata_path, "wb") as f:
        pickle.dump(metadata, f)