"""Sentence Transformer embedding provider."""

from __future__ import annotations

import logging

from backend.app.rag.embeddings import EmbeddingProvider

logger = logging.getLogger(__name__)


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """Local embedding provider using sentence-transformers.
    
    This provider loads a sentence-transformer model locally into memory
    and uses it to generate embeddings.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self._model = None

    def _get_model(self):
        if self._model is None:
            # Lazy load the model to avoid slow startup for non-RAG operations
            logger.info(f"Loading embedding model: {self.model_name}")
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
            except ImportError:
                raise RuntimeError("sentence-transformers is not installed. Please install it to use this provider.")
        return self._model

    async def embed_text(self, text: str) -> list[float]:
        """Return one embedding vector for a text value."""
        model = self._get_model()
        # SentenceTransformer.encode returns a numpy array, we convert to list of floats
        embedding = model.encode(text)
        return embedding.tolist()

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per text value."""
        if not texts:
            return []
        model = self._get_model()
        embeddings = model.encode(texts)
        return [embedding.tolist() for embedding in embeddings]
