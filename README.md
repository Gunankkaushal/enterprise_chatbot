# Enterprise RAG Pipeline 
This repository contains a robust, department-isolated Retrieval-Augmented Generation (RAG) system. It is designed to ingest enterprise documents (PDF, DOCX), intelligently process and chunk the text, and answer user queries with strictly cited, hallucination-free responses using the Gemini LLM.

## Key Features
- Departmental Isolation: Vector indexes are physically and logically separated by department, ensuring absolute data privacy and scoped retrieval.

- Advanced Document Cleaning: Custom weighted algorithms detect and strip repeating headers and footers from PDFs, preventing noisy embeddings.

- Granular Metadata Tracking: Every chunk retains its lineage, including the source filename, page number, and document-level context.

- Inline Citations: The LLM is strictly prompted to cite its sources directly in the text (e.g., [Source: handbook.pdf, Page: 4]).

- Smart Fallbacks: If the provided documents do not contain the answer, the LLM politely declines to hallucinate and instead generates relevant Clarifying Questions to help guide the user.

## The RAG Pipeline Workflow
The pipeline is split into two main flows: Data Ingestion (`/upload`) and Query Generation (`/ask`).

### Phase 1: Data Ingestion & Indexing
1. Document Parsing & Cleaning (`utils/parsers.py` & `utils/helpers.py`)

    - Files are accepted via the `/upload endpoint.
    - PDFs (PyMuPDF): Text is extracted page-by-page. A custom algorithm calculates the occurrence of lines at the extreme top and bottom of pages. Common repeating lines (headers/footers) are stripped out, while the first header instance is preserved as global `doc_context`.
    - Text Normalization: Text passes through a pipeline that resolves unicode anomalies, rejoins hyphenated words broken across lines, expands ligatures (e.g., ﬁ -> fi), and collapses redundant whitespace.

2. Context-Aware Chunking (`services/nlp_service.py`)

    - The cleaned text is passed to LlamaIndex's SentenceSplitter.
    - Unlike standard text splitters, this implementation maps the generated chunks into LlamaIndex TextNode objects.
    - Crucially, metadata (`source`, `page_number`, `chunk_number`, `doc_context`) is explicitly attached to each node, ensuring page-level tracking survives the chunking process.

3. Embedding & Vector Storage (`services/vector_store.py`)

    - Embedding Model: Chunks are vectorized using the lightweight, highly efficient `all-MiniLM-L6-v2` model via sentence-transformers.
    - Storage: The vectors are stored in FAISS (Facebook AI Similarity Search) using IndexFlatL2.
    - Departmental Routing: The system dynamically loads or creates a FAISS index directory based on the department_name. The text and metadata are serialized into a synchronized metadata.pkl file alongside the .faiss index.

### Phase 2: Retrieval & Generation
1. Semantic Retrieval (`services/retriever_service.py`)

    - When a user submits a query to the /ask endpoint, the query is embedded using the same `all-MiniLM-L6-v2` model.
    - The system loads the specific FAISS index for the requested department_id and performs an L2 distance search to retrieve the Top-K closest vector matches.
    - A strict post-retrieval validation ensures no cross-department data leakage.
    - The matching metadata is used to instantly reconstruct the original LlamaIndex TextNodes.

2. Prompt Engineering & LLM Execution (`services/llm_service.py`)

    - Model: Google Gemini (gemini-2.5-flash).
    - Context Injection: The retrieved nodes are formatted into a prompt blocks with explicit source tags (e.g., [Source: hr_policy.pdf, Page: 12]).
    - Strict Ruleset: The LLM is instructed to act as a departmental expert and is bound by rigid rules:
        - Rule A: Answer directly and provide inline citations mapping to the context blocks.
        - Rule B: If information is missing, output Status: Insufficient Information.
        - Rule C: If insufficient, generate up to 3 clarifying follow-up questions.

3. Response Formatting (`routes/ask.py`)

    - The raw LLM output is parsed using regular expressions to separate the final text answer, the status, and any clarifying_questions.
    - The endpoint compiles a deduplicated list of sources (filename, page number, and vector distance score) and returns a clean, structured JSON response to the client.

## Tech Stack
- Framework: FastAPI (Python 3.10+)
- Vector Store: FAISS (faiss-cpu)
- Embeddings: sentence-transformers
- Chunking & Node Parsing: LlamaIndex Core
- LLM Provider: Google Generative AI (gemini-2.5-flash)
- Document Parsing: PyMuPDF, python-docx
- Database: SQLAlchemy (SQLite)