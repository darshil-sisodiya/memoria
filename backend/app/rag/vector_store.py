"""ChromaDB wrapper that keeps vector persistence behind an application API."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings


@dataclass(frozen=True)
class VectorDocument:
    """A document to index in a vector collection."""

    id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VectorSearchResult:
    """A vector search result linked back to SQLite metadata."""

    id: str
    content: str
    score: float
    metadata: dict[str, Any]


class VectorStore:
    """Model-independent vector-store contract."""

    async def add_documents(
        self,
        collection: str,
        documents: list[VectorDocument],
        embeddings: list[list[float]],
    ) -> None:
        raise NotImplementedError

    async def search(
        self,
        collection: str,
        query_embedding: list[float],
        *,
        top_k: int = 8,
        where: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        raise NotImplementedError

    async def delete(self, collection: str, ids: list[str]) -> None:
        raise NotImplementedError

    async def clear_collection(self, collection: str) -> None:
        raise NotImplementedError

    async def get_existing_ids(self, collection: str, ids: list[str]) -> set[str]:
        raise NotImplementedError


class ChromaVectorStore(VectorStore):
    """Persistent local ChromaDB implementation."""

    def __init__(self, path: str | Path, client: Any | None = None) -> None:
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self.client = client or chromadb.PersistentClient(
            path=str(self.path),
            settings=ChromaSettings(
                anonymized_telemetry=False,
                chroma_product_telemetry_impl="backend.app.rag.telemetry.NoOpTelemetry",
            ),
        )
        self._collections: dict[str, Any] = {}

    def _get_collection(self, name: str) -> Any:
        if name not in self._collections:
            self._collections[name] = self.client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collections[name]

    async def add_documents(
        self,
        collection: str,
        documents: list[VectorDocument],
        embeddings: list[list[float]],
    ) -> None:
        if len(documents) != len(embeddings):
            raise ValueError("Each vector document must have one embedding")
        if not documents:
            return

        chroma_collection = self._get_collection(collection)
        chroma_collection.upsert(
            ids=[document.id for document in documents],
            documents=[document.content for document in documents],
            embeddings=embeddings,
            metadatas=[self._clean_metadata(document.metadata) for document in documents],
        )

    async def search(
        self,
        collection: str,
        query_embedding: list[float],
        *,
        top_k: int = 8,
        where: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        if top_k < 1:
            return []

        chroma_collection = self._get_collection(collection)
        collection_size = chroma_collection.count()
        if collection_size == 0:
            return []
        query_kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": min(top_k, collection_size),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            query_kwargs["where"] = where

        raw = chroma_collection.query(**query_kwargs)
        ids = raw.get("ids", [[]])[0]
        documents = raw.get("documents", [[]])[0]
        metadatas = raw.get("metadatas", [[]])[0]
        distances = raw.get("distances", [[]])[0]

        return [
            VectorSearchResult(
                id=ids[index],
                content=documents[index] or "",
                score=1.0 - float(distances[index]),
                metadata=metadatas[index] or {},
            )
            for index in range(len(ids))
        ]

    async def delete(self, collection: str, ids: list[str]) -> None:
        if ids:
            self._get_collection(collection).delete(ids=ids)

    async def clear_collection(self, collection: str) -> None:
        if collection in self._collections:
            del self._collections[collection]
        try:
            self.client.delete_collection(collection)
        except Exception as error:
            if "not found" not in str(error).lower():
                raise

    async def get_existing_ids(self, collection: str, ids: list[str]) -> set[str]:
        if not ids:
            return set()
        chroma_collection = self._get_collection(collection)
        result = chroma_collection.get(ids=ids, include=[])
        return set(result.get("ids", []))
    @staticmethod
    def _clean_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in metadata.items()
            if value is not None and isinstance(value, (str, int, float, bool))
        }
