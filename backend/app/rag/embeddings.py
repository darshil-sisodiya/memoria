"""Embedding provider abstractions and the deterministic local mock provider."""

from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Model-independent interface for text embeddings."""

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """Return one embedding vector for a text value."""

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per text value."""


class MockEmbeddingProvider(EmbeddingProvider):
    """Create deterministic local vectors without downloading a model.

    This is intentionally a test/development provider. It hashes normalized
    tokens into a fixed-size vector, which gives repeatable lexical similarity
    while keeping the production embedding model replaceable.
    """

    def __init__(self, dimension: int = 64) -> None:
        if dimension < 8:
            raise ValueError("Embedding dimension must be at least 8")
        self.dimension = dimension
        self._token_pattern = re.compile(r"[\w']+", re.UNICODE)

    async def embed_text(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = self._token_pattern.findall(text.lower())

        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            magnitude = 0.5 + (digest[4] / 255.0)
            sign = 1.0 if digest[5] % 2 else -1.0
            vector[index] += sign * magnitude

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            vector[0] = 1.0
            norm = 1.0
        return [value / norm for value in vector]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed_text(text) for text in texts]

