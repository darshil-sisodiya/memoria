"""Indexer service for persisting RAG chunks to the vector store."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.models import Message
from backend.app.rag.chunking import ConversationChunker
from backend.app.rag.embeddings import EmbeddingProvider
from backend.app.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


class IndexerService:
    """Service to process imported messages into semantic chunks and index them."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        chunker: ConversationChunker | None = None,
    ) -> None:
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.chunker = chunker or ConversationChunker()

    async def index_person_messages(self, session: Session, person_id: int) -> dict[str, int]:
        """Index all messages for a specific person into the vector store.
        
        Returns a dictionary with stats: chunks_processed, chunks_indexed, chunks_skipped.
        """
        # Fetch all messages ordered chronologically
        query = select(Message).where(Message.person_id == person_id).order_by(Message.timestamp.asc())
        result = session.execute(query)
        messages = list(result.scalars().all())

        if not messages:
            return {"chunks_processed": 0, "chunks_indexed": 0, "chunks_skipped": 0}

        # Create chunks
        chunks = self.chunker.create_chunks(messages)
        if not chunks:
            return {"chunks_processed": 0, "chunks_indexed": 0, "chunks_skipped": 0}

        # Identify which chunks already exist
        chunk_ids = [chunk.id for chunk in chunks]
        existing_ids = await self.vector_store.get_existing_ids("messages", chunk_ids)

        chunks_to_index = [chunk for chunk in chunks if chunk.id not in existing_ids]

        if chunks_to_index:
            logger.info(f"Embedding {len(chunks_to_index)} new conversation chunks")
            texts_to_embed = [chunk.content for chunk in chunks_to_index]
            embeddings = await self.embedding_provider.embed_batch(texts_to_embed)
            
            logger.info(f"Persisting {len(chunks_to_index)} chunks to vector store")
            await self.vector_store.add_documents("messages", chunks_to_index, embeddings)

        return {
            "chunks_processed": len(chunks),
            "chunks_indexed": len(chunks_to_index),
            "chunks_skipped": len(existing_ids),
        }
