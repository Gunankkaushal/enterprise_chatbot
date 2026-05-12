import argparse
from pathlib import Path
from typing import List

from services.pdf_loader import load_and_split_pdf
from services.vector_store import LocalFaissStore, Document

try:
    from services.openai_client import OpenAIEmbeddingsClient
except Exception:
    OpenAIEmbeddingsClient = None


class FakeEmbeddings:
    def __init__(self, dim: int = 1536):
        import random
        self.dim = dim
        self._rand = random.Random(42)

    def embed_documents(self, texts: List[str]):
        import numpy as np
        return [np.array([self._rand.random() for _ in range(self.dim)], dtype="float32") for _ in texts]

    def embed_query(self, text: str):
        import numpy as np
        return np.array([0.0 for _ in range(self.dim)], dtype="float32")


def gather_documents(upload_dir: Path) -> List[Document]:
    docs: List[Document] = []
    for pdf in sorted(upload_dir.glob("*.pdf")):
        print(f"Reading: {pdf}")
        pages = load_and_split_pdf(pdf)
        docs.extend(pages)
    return docs


def main(dry_run: bool = False):
    uploads = Path("uploads")
    if not uploads.exists():
        raise SystemExit("uploads/ directory not found; place PDFs in uploads/")

    documents = gather_documents(uploads)
    if not documents:
        raise SystemExit("No PDF pages found in uploads/ — add PDFs and retry.")

    if dry_run:
        print("Dry-run: using fake embeddings to build index")
        embeddings = FakeEmbeddings()
    else:
        if OpenAIEmbeddingsClient is None:
            raise SystemExit("OpenAIEmbeddingsClient unavailable; install or use --dry-run")
        embeddings = OpenAIEmbeddingsClient()

    print(f"Creating FAISS index for {len(documents)} chunks...")
    store = LocalFaissStore.from_documents(documents, embeddings)
    store.save_local("vectorstore/faiss_index")
    print("Index saved to vectorstore/faiss_index")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest PDFs into FAISS vectorstore")
    parser.add_argument("--dry-run", action="store_true", help="Build index with fake embeddings for testing")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
