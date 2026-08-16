"""Embedding and local ChromaDB tests."""

import asyncio
from pathlib import Path

from backend.app.rag.embeddings import MockEmbeddingProvider
from backend.app.rag.vector_store import ChromaVectorStore, VectorDocument


def test_mock_embeddings_are_deterministic_and_searchable(tmp_path: Path) -> None:
    async def scenario() -> None:
        provider = MockEmbeddingProvider(dimension=32)
        store = ChromaVectorStore(tmp_path / "chroma")
        documents = [
            VectorDocument(
                id="memory:1",
                content="Mysore trip during Christmas",
                metadata={"source_type": "memory", "source_id": 1, "person_id": 1},
            ),
            VectorDocument(
                id="memory:2",
                content="Made dosa for breakfast",
                metadata={"source_type": "memory", "source_id": 2, "person_id": 2},
            ),
        ]
        embeddings = await provider.embed_batch([document.content for document in documents])
        assert embeddings[0] == await provider.embed_text(documents[0].content)
        assert len(embeddings[0]) == 32

        await store.add_documents("memories", documents, embeddings)
        results = await store.search(
            "memories",
            await provider.embed_text("Do you remember the Mysore trip?"),
            top_k=2,
            where={"person_id": 1},
        )

        assert len(results) == 1
        assert results[0].id == "memory:1"
        assert results[0].metadata["source_id"] == 1
        assert await store.search("empty", embeddings[0]) == []

    asyncio.run(scenario())

