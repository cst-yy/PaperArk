"""Embedding generation for text chunks using sentence-transformers."""

from app.core.config import settings


class EmbeddingService:
    """Generate vector embeddings for text chunks."""

    def __init__(self):
        self._model = None

    @property
    def model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(settings.EMBEDDING_MODEL)
            except ImportError:
                return None
        return self._model

    def embed(self, text: str) -> list[float] | None:
        """Generate embedding for a single text."""
        model = self.model
        if model is None:
            return None
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]] | None:
        """Generate embeddings for multiple texts."""
        model = self.model
        if model is None:
            return None
        embeddings = model.encode(texts, normalize_embeddings=True, batch_size=32)
        return [e.tolist() for e in embeddings]

    def embed_query(self, query: str) -> list[float] | None:
        """Generate embedding for a search query."""
        return self.embed(query)


embedding_service = EmbeddingService()
