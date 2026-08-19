"""Retrieval service for RAG."""

from __future__ import annotations

import logging
from typing import Any

from backend.app.rag.embeddings import EmbeddingProvider
from backend.app.rag.vector_store import VectorSearchResult, VectorStore

logger = logging.getLogger(__name__)


class RetrievalService:
    """Service for querying semantic memories and conversation history."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
    ) -> None:
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store

    async def retrieve_history(
        self,
        query: str,
        top_k: int = 5,
        person_id: int | None = None,
    ) -> list[VectorSearchResult]:
        """Retrieve the most relevant historical conversation chunks for a query."""
        if not query.strip() or top_k < 1:
            return []

        try:
            # Embed the search query
            query_embedding = await self.embedding_provider.embed_text(query)

            # Build filters
            where: dict[str, Any]
            if person_id is not None and person_id > 0:
                where = {
                    "$and": [
                        {"source_type": "conversation_chunk"},
                        {"person_id": person_id}
                    ]
                }
            else:
                where = {"source_type": "conversation_chunk"}

            # Search Chroma
            results = await self.vector_store.search(
                collection="messages",
                query_embedding=query_embedding,
                top_k=top_k,
                where=where,
            )
            
            logger.info(f"Retrieved {len(results)} relevant conversation chunks for query")
            return results

        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            # Ensure we gracefully degrade if vector store/embedding fails
            return []
