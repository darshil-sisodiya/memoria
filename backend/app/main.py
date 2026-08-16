"""FastAPI application entry point for Memoria AI."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from sqlalchemy import text

from backend.app.api.chat import router as chat_router
from backend.app.api.conversations import router as conversations_router
from backend.app.api.health import router as health_router
from backend.app.api.imports import router as imports_router
from backend.app.api.memories import router as memories_router
from backend.app.api.people import router as people_router
from backend.app.core.config import Settings, get_settings
from backend.app.core.logging import configure_logging, get_logger
from backend.app.database.database import create_db_engine, create_session_factory
from backend.app.rag.embeddings import MockEmbeddingProvider
from backend.app.rag.vector_store import ChromaVectorStore


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create a configured FastAPI application.

    Keeping application creation in a function makes tests independent from the
    developer's local database and environment.
    """

    app_settings = settings or get_settings()
    configure_logging(app_settings.log_level)
    logger = get_logger(__name__)
    engine = create_db_engine(app_settings.database_url)
    embedding_provider = MockEmbeddingProvider()
    vector_store = ChromaVectorStore(app_settings.chroma_path)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        app_settings.data_path.mkdir(parents=True, exist_ok=True)
        app_settings.models_path.mkdir(parents=True, exist_ok=True)
        app_settings.storage_path.mkdir(parents=True, exist_ok=True)
        app_settings.chroma_path.mkdir(parents=True, exist_ok=True)

        # This verifies connectivity and creates the SQLite file when using the
        # default local URL. Schema changes remain the responsibility of Alembic.
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("server_started")
        yield
        engine.dispose()

    app = FastAPI(
        title="Memoria AI API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = app_settings
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.embedding_provider = embedding_provider
    app.state.vector_store = vector_store
    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(people_router)
    app.include_router(memories_router)
    app.include_router(conversations_router)
    app.include_router(imports_router)
    return app


app = create_app()
