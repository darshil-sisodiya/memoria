"""FastAPI dependency helpers."""

from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from backend.app.rag.embeddings import EmbeddingProvider
from backend.app.rag.vector_store import VectorStore


def get_db(request: Request) -> Generator[Session, None, None]:
    """Yield a request-scoped SQLAlchemy session."""

    session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


def get_embedding_provider(request: Request) -> EmbeddingProvider:
    """Return the configured embedding provider."""

    return request.app.state.embedding_provider


def get_vector_store(request: Request) -> VectorStore:
    """Return the configured vector store."""

    return request.app.state.vector_store
