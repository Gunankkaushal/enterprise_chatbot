from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import uuid


def create_vector_store(chunks):

    # Add unique IDs to every chunk
    for chunk in chunks:
        chunk.id = str(uuid.uuid4())

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vectorstore = FAISS.from_documents(
        chunks,
        embeddings
    )

    vectorstore.save_local("vectorstore/faiss_index")

    return vectorstore