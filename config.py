import os

UPLOAD_DIR = "store/uploaded_files"
FAISS_DIR = "store/faiss_indexes"
TOP_K_CHUNKS = 5

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(FAISS_DIR, exist_ok=True)