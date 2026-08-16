# Memoria AI

Memoria AI is a local-first memory companion. The project is being built incrementally, with SQLite as the structured-data source of truth and model providers kept behind replaceable interfaces.

## Current milestone: Phase 1

This milestone contains only the initial backend setup:

- FastAPI application
- SQLite and SQLAlchemy 2.x configuration
- Alembic migration setup
- Initial database models
- `GET /api/health`
- People, memory, and conversation persistence APIs
- WhatsApp `.txt` import with multiline-message parsing
- Deterministic local embeddings and persistent ChromaDB indexing
- Synthetic health, CRUD, parser, and import tests

The frontend, ChromaDB, RAG pipeline, and LLM providers are intentionally not implemented yet.

RAG retrieval, LLM providers, and the frontend are still deferred; the embedding and vector-store layer is now available as part of the current backend milestone.

## Requirements

- Python 3.11+

Rust/Tauri and Node.js will be needed in a later frontend phase.

## Backend setup

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
alembic -c backend\alembic.ini upgrade head
```

## Run the backend

```powershell
python -m uvicorn backend.app.main:app --reload
```

Then open <http://127.0.0.1:8000/api/health>.

## Current API endpoints

```text
GET    /api/health
GET    /api/people
POST   /api/people
GET    /api/people/{id}
GET    /api/memories?person_id={id}
POST   /api/memories
GET    /api/memories/{id}
DELETE /api/memories/{id}
GET    /api/conversations?person_id={id}
POST   /api/conversations
GET    /api/conversations/{id}
POST   /api/import/whatsapp
```

The WhatsApp import endpoint accepts a multipart form with `person_id` and a `.txt` file. It supports common dash and bracketed headers, preserves multiline messages, and stores imported rows in SQLite with `source="whatsapp"`.

## Run tests

```powershell
python -m pytest backend/tests -q
```

## Configuration

The backend uses local defaults and can be configured with environment variables:

- `DATABASE_URL` (default: `sqlite:///./storage/memoria.db`)
- `DATA_PATH` (default: `data`)
- `MODELS_PATH` (default: `models`)
- `STORAGE_PATH` (default: `storage`)
- `CHROMA_PATH` (default: `storage/chroma`)
- `LOG_LEVEL` (default: `INFO`)

## Embeddings and ChromaDB

The backend keeps SQLite as the source of truth. A local `MockEmbeddingProvider` creates deterministic vectors for development, and `ChromaVectorStore` persists them under `storage/chroma` with telemetry disabled.

Messages are stored in the `messages` collection and memories in the `memories` collection. Each vector includes SQLite references such as `source_type`, `source_id`, `person_id`, and `timestamp`.

The mock provider can later be replaced by a local embedding model without changing the import, memory, or retrieval services.

No cloud AI service or telemetry is used.
