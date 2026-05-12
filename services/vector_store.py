from dataclasses import dataclass, field
from pathlib import Path
import pickle
from typing import Any

import faiss
import numpy as np


@dataclass
class Document:
    page_content: str
    metadata: dict[str, Any] = field(default_factory=dict)


class LocalRetriever:
    def __init__(self, vector_store, k: int = 3):
        self.vector_store = vector_store
        self.k = k

    def invoke(self, query: str):
        return self.vector_store.similarity_search(query, self.k)


class LocalFaissStore:
    def __init__(self, index, documents, embeddings):
        self.index = index
        self.documents = documents
        self.embeddings = embeddings

    @classmethod
    def from_documents(cls, documents, embeddings):
        texts = [document.page_content for document in documents]
        vectors = np.array(embeddings.embed_documents(texts), dtype="float32")

        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)

        faiss.normalize_L2(vectors)
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)
        return cls(index=index, documents=list(documents), embeddings=embeddings)

    @classmethod
    def load_local(cls, folder_path, embeddings):
        folder = Path(folder_path)
        index_path = folder / "index.faiss"
        documents_path = folder / "documents.pkl"

        if not index_path.exists() or not documents_path.exists():
            raise FileNotFoundError(
                f"Missing FAISS files in {folder}. Run the PDF ingest flow first."
            )

        index = faiss.read_index(str(index_path))
        with documents_path.open("rb") as handle:
            documents = pickle.load(handle)

        return cls(index=index, documents=documents, embeddings=embeddings)

    def save_local(self, folder_path):
        folder = Path(folder_path)
        folder.mkdir(parents=True, exist_ok=True)

        faiss.write_index(self.index, str(folder / "index.faiss"))
        with (folder / "documents.pkl").open("wb") as handle:
            pickle.dump(self.documents, handle)

    def as_retriever(self, search_kwargs=None):
        search_kwargs = search_kwargs or {}
        return LocalRetriever(self, k=search_kwargs.get("k", 3))

    def similarity_search(self, query, k: int = 3):
        query_vector = np.array([self.embeddings.embed_query(query)], dtype="float32")
        faiss.normalize_L2(query_vector)

        scores, indices = self.index.search(query_vector, k)
        results = []
        for index in indices[0]:
            if index == -1:
                continue
            results.append(self.documents[int(index)])
        return results