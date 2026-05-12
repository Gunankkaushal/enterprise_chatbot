from pathlib import Path

import pypdf

from services.vector_store import Document


def _split_text(text, chunk_size=500, chunk_overlap=50):
    cleaned_text = text.strip()
    if not cleaned_text:
        return []

    step = max(1, chunk_size - chunk_overlap)
    chunks = []
    for start in range(0, len(cleaned_text), step):
        chunk = cleaned_text[start:start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def load_and_split_pdf(pdf_path):
    reader = pypdf.PdfReader(pdf_path)
    documents = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        for chunk_number, chunk in enumerate(_split_text(text), start=1):
            documents.append(
                Document(
                    page_content=chunk,
                    metadata={
                        "source": str(Path(pdf_path)),
                        "page": page_number,
                        "chunk": chunk_number,
                    },
                )
            )

    return documents