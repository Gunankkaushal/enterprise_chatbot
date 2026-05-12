# Enterprise Chatbot

Enterprise knowledge chatbot built with FastAPI, FAISS, and PDF ingestion. The project ingests PDF files, builds a vector index, and serves question-answering over the indexed content.

## Features

- PDF ingestion with chunking
- Local FAISS vector index storage
- FastAPI endpoint for question answering
- Department-based metadata flow in chat logic
- Optional MongoDB collections for chat/document logging

## Project Structure

- `api.py`: FastAPI entrypoint (`/ask`)
- `ingest.py`: PDF ingest and FAISS index creation
- `app.py`: Interactive local script flow
- `services/`: Chatbot, vector store, loaders, and integrations
- `uploads/`: Place source PDFs here
- `vectorstore/faiss_index/`: Saved FAISS artifacts

## Prerequisites

- Python 3.10+
- Optional: MongoDB running locally (`mongodb://localhost:27017/`)
- Optional: Ollama with `tinyllama` model for current chatbot implementation

## Environment Variables

Create `.env` in the repository root:

```env
OPENAI_API_KEY=your_openai_api_key
```

`OPENAI_API_KEY` is required for flows that use `services/openai_client.py`.

## Setup

```bash
python -m venv venv
# Windows PowerShell
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Ingest PDFs

1. Add PDF files into `uploads/`.
2. Run ingest:

```bash
python ingest.py
```

For offline test indexing without OpenAI embeddings:

```bash
python ingest.py --dry-run
```

## Run API

```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

Example request:

```text
GET /ask?query=What%20is%20leave%20policy%3F&role=HR
```

## Development Notes

- `app.py` is an interactive script and may need alignment with the local FAISS/OpenAI flow depending on your preferred runtime.
- Keep generated index files out of git for reproducibility.

## License

MIT (or update to your preferred license)
