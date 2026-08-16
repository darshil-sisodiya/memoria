"""Memory application service."""

from datetime import datetime

from sqlalchemy.orm import Session

from backend.app.database.models import Memory
from backend.app.database.repositories.memories import MemoryRepository
from backend.app.rag.embeddings import EmbeddingProvider
from backend.app.rag.vector_store import VectorDocument, VectorStore


class MemoryService:
    """Coordinate SQLite-backed memory operations.

    Vector synchronization is intentionally deferred to the embeddings/RAG
    phase, where the VectorStore abstraction will be introduced.
    """

    def __init__(
        self,
        repository: MemoryRepository | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:
        self.repository = repository or MemoryRepository()
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store

    def list_memories(self, session: Session, person_id: int | None = None) -> list[Memory]:
        return self.repository.list(session, person_id)

    def get_memory(self, session: Session, memory_id: int) -> Memory | None:
        return self.repository.get(session, memory_id)

    async def create_memory(
        self,
        session: Session,
        *,
        person_id: int,
        title: str,
        content: str,
        timestamp: datetime | None,
        source: str,
        source_id: str | None,
        importance: int,
    ) -> Memory:
        memory = Memory(
            person_id=person_id,
            title=title,
            content=content,
            timestamp=timestamp,
            source=source,
            source_id=source_id,
            importance=importance,
        )
        session.add(memory)
        session.flush()
        vector_id = f"memory:{memory.id}"
        try:
            if self.embedding_provider is None or self.vector_store is None:
                raise RuntimeError("Embedding and vector-store providers are required for memories")
            embedding = await self.embedding_provider.embed_text(f"{memory.title}\n{memory.content}")
            await self.vector_store.add_documents(
                "memories",
                [
                    VectorDocument(
                        id=vector_id,
                        content=f"{memory.title}: {memory.content}",
                        metadata={
                            "source_type": "memory",
                            "source_id": memory.id,
                            "person_id": memory.person_id,
                            "timestamp": memory.timestamp.isoformat() if memory.timestamp else None,
                        },
                    )
                ],
                [embedding],
            )
            session.commit()
            session.refresh(memory)
            return memory
        except Exception:
            session.rollback()
            if self.vector_store is not None:
                await self.vector_store.delete("memories", [vector_id])
            raise

    async def delete_memory(self, session: Session, memory: Memory) -> None:
        vector_id = f"memory:{memory.id}"
        self.repository.delete(session, memory)
        if self.vector_store is not None:
            await self.vector_store.delete("memories", [vector_id])
