# Memoria AI

Memoria AI is a local-first memory companion. The project is being built incrementally, with SQLite as the structured-data source of truth and model providers kept behind replaceable interfaces.

## Development Model

The core philosophy of Memoria AI is **local-first** and **privacy-first**:
- Model files (GGUFs) are kept outside the source repository.
- Inference is handled locally by `llama-server` running outside of the Memoria application.
- Memoria communicates with the local model over localhost.
- SQLite is the current source of truth for all imported messages and conversational data.
- ChromaDB handles vector embeddings for semantic retrieval. Durable memory extraction is planned for future work.
- **No cloud inference or telemetry is used** for the current local LLM path or embeddings.

## Current Architecture

The current implementation bridges WhatsApp chat preservation with local LLM inference via a working Retrieval-Augmented Generation (RAG) pipeline.

```text
                    MEMORIA

       WhatsApp TXT export
                |
                v
       WhatsApp Parser
                |
                v
          ImportService
                |
                v
             SQLite
                |
                |-----> Embeddings
                |          |
                |          v
                |       ChromaDB
                |          |
                |          v
                |       Retrieval
                |          |
                |          v
Memoria API ---> LocalLlamaProvider
                       |
                       | HTTP
                       v
                  llama-server
                       |
                       v
                   GGUF Model
```

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

## How to Start `llama-server`

Memoria does not directly load the GGUF model binary. Inference must be provided by a local instance of `llama-server` (from the `llama.cpp` project), which should be started separately.

Start the server using a command similar to:

```powershell
llama-server.exe ^
  -m "D:\path\to\your\model.gguf" ^
  -ngl 999 ^
  --ctx-size 2048 ^
  --port 8080
```

- Replace the model path with the actual location of your GGUF model (which does not need to be inside the Memoria repository).
- `-ngl 999` enables maximum GPU offloading when supported by your hardware.
- `--ctx-size` controls the context window size.
- `--port` determines the local HTTP port the server binds to.

## Configuration

The backend uses local defaults and can be configured with environment variables:

- `DATABASE_URL` (default: `sqlite:///./storage/memoria.db`)
- `DATA_PATH` (default: `data`)
- `MODELS_PATH` (default: `models`)
- `STORAGE_PATH` (default: `storage`)
- `CHROMA_PATH` (default: `storage/chroma`)
- `LOG_LEVEL` (default: `INFO`)

**Local LLM Configuration:**
- `LLM_PROVIDER` (default: `local`)
- `LLM_BASE_URL` (default: `http://127.0.0.1:8080/v1`)
- `LLM_MODEL` (default: `local-model`)

These are fully configurable. For example, if you run your `llama-server` on port 9000 instead of 8080, you can configure Memoria accordingly:

```powershell
$env:LLM_BASE_URL="http://127.0.0.1:9000/v1"
```

The model server and Memoria must use matching ports.

## Run the backend

Start Memoria via Uvicorn:

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
POST   /api/chat
```

The WhatsApp import endpoint accepts a multipart form with `person_id` and a `.txt` file. It supports common dash and bracketed headers, preserves multiline messages, and stores imported rows in SQLite with `source="whatsapp"`.

## Swagger UI / API Testing

Memoria currently exposes a development chat endpoint (`POST /api/chat`) that can be tested directly without a frontend using the FastAPI Swagger UI.

**Testing Sequence:**
1. Start `llama-server` on your chosen port.
2. Start the Memoria backend.
3. Open http://127.0.0.1:8000/docs
4. Find the `POST /api/chat` endpoint and click "Try it out".
5. Submit a request using a payload like:

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are Darshil."
    },
    {
      "role": "user",
      "content": "Hello!"
    }
  ],
  "temperature": 0.7
}
```
6. Inspect the generated response. 

*Note: Setting `"use_memory": true` in the JSON payload triggers the Retrieval-Augmented Generation (RAG) pipeline. This retrieves relevant historical conversation chunks from ChromaDB and injects them into the system prompt for the local LLM. If `false` or omitted, it forwards the messages directly to the LLM without retrieval.*

## WhatsApp Importer

Memoria contains a canonical, highly-tested WhatsApp importer. The importer supports:
- Standard WhatsApp TXT exports
- Chronological message preservation
- Sender names and timestamps
- Multiline messages
- Unicode and emojis
- Media placeholders
- System messages, encryption notices, and malformed/unrecognized opening system records

The parser processes the export into structured `ParsedWhatsAppMessage` records, which are passed through Memoria's `ImportService` directly into SQLite. SQLite serves as the source of truth for imported conversation data.

*(Note: The standalone Finetuning parser project has been fully migrated into this repository and is no longer an active dependency).*

### Verified Import Results

The migrated parser has been verified against the original Finetuner baseline and produced matching results, successfully passing through the `ImportService` into SQLite with no missing or duplicate messages:
- Input lines: 24,174
- Parsed messages: 19,669
- Multiline messages: 204
- System messages: 10
- Media placeholders: 7
- Unique speakers: 4
- Earliest timestamp: 2025-05-26 19:29:05
- Latest timestamp: 2026-08-14 23:06:44

### Test Fixture

The real WhatsApp export used for regression testing is stored at:
`backend/tests/data/whatsapp/chat.txt`

This fixture allows the parser to be tested against a real-world WhatsApp export format. 

> **IMPORTANT PRIVACY NOTE:**
> Real WhatsApp exports contain private conversations and personal information. The repository should remain private if real conversation data is included, and sensitive chat exports must never be committed to a public repository.

## Local LLM Provider Design

Memoria interacts with `llama-server` via a `LocalLlamaProvider` which implements the base `LLMProvider` abstraction. This abstraction exists so that the rest of Memoria does not need to be tightly coupled to `llama.cpp`. 

The provider utilizes `httpx` to communicate with the OpenAI-compatible HTTP API (`/v1`) exposed by `llama-server`. (We intentionally do not use `llama-cpp-python` for this integration).

Current provider responsibilities include:
- Health checking the local server
- Sending chat completion requests
- Parsing generated responses
- Handling connection failures
- Handling timeouts
- Handling HTTP errors
- Handling malformed/empty responses

## Experimental Local Fine-Tuned Model

Alongside the Memoria project, experimental fine-tuning work has been conducted. The initial experiment utilized:
`Qwen2.5-3B-Instruct` + `QLoRA` + `WhatsApp conversation dataset` + `Unsloth Studio`.

The resulting fine-tuned model was exported to GGUF format and is successfully being tested through `llama-server` using Memoria's `LocalLlamaProvider`. This experimental result demonstrated recognizable conversational style changes compared to the base Qwen model (e.g., shorter responses, slang usage, emoji/sticker behavioral quirks). Note that this is an experimental result, not a claim that the model perfectly reproduces a person's identity or personality.

## Run tests

```powershell
python -m pytest backend/tests -q
```

**Current verified state (32 tests total):**
- WhatsApp parser tests: 6/6 pass
- LocalLlamaProvider tests pass
- RAG pipeline tests (chunking, indexing, retrieval, context generation): pass
- Full Memoria test suite: 32/32 pass
- ImportService successfully imports all records cleanly to SQLite
- Local inference integration with dynamic memory retrieval has been verified through `/api/chat`

## Embeddings and ChromaDB

The backend keeps SQLite as the primary source of truth. The application uses `sentence-transformers/all-MiniLM-L6-v2` locally via the `SentenceTransformerEmbeddingProvider` to create embeddings, and `ChromaVectorStore` persists them under `storage/chroma` with telemetry disabled. No cloud AI service is used.

### Reindexing & Chunking
Rather than embedding single messages, historical WhatsApp conversations are intelligently chunked using `ConversationChunker`. The chunker groups continuous blocks of conversation together up to a ~3,000 character maximum, enforcing a 30-minute idle boundary between separate conversation chunks.

To batch-process and index an imported WhatsApp export from SQLite to ChromaDB, use the indexing script:
```powershell
python backend/scripts/reindex.py
```

## Roadmap & Planned Features

The following features are **FUTURE/PLANNED** work and are not currently implemented:
- Memory extraction
- Automatic model management
- Desktop frontend
- Mobile application
- Packaging/distribution
- Raspberry Pi deployment
- Multimodal memory such as images/stickers/voice
