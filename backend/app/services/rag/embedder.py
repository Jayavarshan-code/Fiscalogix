"""
Embedder — converts text into dense vector representations.

Model: sentence-transformers/all-MiniLM-L6-v2
  - 384 dimensions
  - Runs entirely on CPU (no GPU required)
  - ~80ms per batch of 64 chunks on a standard server
  - Apache 2.0 license — no API cost

The model is loaded once at import time (singleton pattern).
Subsequent calls hit the cached model instance.
"""

import logging
import json
from typing import List

logger = logging.getLogger(__name__)


class Embedder:
    """
    Wraps sentence-transformers for text → vector conversion.
    Fails gracefully to None vectors if the library is not installed —
    the retriever falls back to keyword search in that case.
    """

    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    DIMENSIONS = 384

    def __init__(self):
        self._model = None
        self._load()

    def _load(self):
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.MODEL_NAME)
            logger.info(f"Embedder: loaded {self.MODEL_NAME} ({self.DIMENSIONS}d)")
        except ImportError:
            logger.warning(
                "Embedder: sentence-transformers not installed. "
                "Run: pip install sentence-transformers. "
                "RAG will fall back to keyword search."
            )
        except Exception as e:
            logger.error(f"Embedder: model load failed — {e}")

    @property
    def ready(self) -> bool:
        return self._model is not None

    def embed(self, text: str) -> List[float] | None:
        """Embed a single string. Returns None if model unavailable."""
        if not self._model:
            return None
        try:
            vec = self._model.encode(text, normalize_embeddings=True)
            return vec.tolist()
        except Exception as e:
            logger.error(f"Embedder.embed: {e}")
            return None

    def embed_batch(self, texts: List[str]) -> List[List[float] | None]:
        """
        Embed a list of strings in one forward pass (faster than per-item).
        Returns list of vectors in same order as input.
        """
        if not self._model:
            return [None] * len(texts)
        try:
            vecs = self._model.encode(texts, normalize_embeddings=True, batch_size=64)
            return [v.tolist() for v in vecs]
        except Exception as e:
            logger.error(f"Embedder.embed_batch: {e}")
            return [None] * len(texts)

    def to_json(self, vector: List[float]) -> str:
        """Serialize a vector for storage in the embedding_json column."""
        return json.dumps(vector)

    def from_json(self, json_str: str) -> List[float]:
        """Deserialize a stored vector."""
        return json.loads(json_str)

    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """
        Pure-Python cosine similarity for fallback retrieval
        when pgvector is not available.
        """
        import math
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(x * x for x in b))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)


# Module-level singleton — loaded once when this module is first imported
_embedder: Embedder | None = None


def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder
