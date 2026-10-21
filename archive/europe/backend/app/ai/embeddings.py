"""Local sentence-transformer embedding model.

The model is loaded once on first use and reused for every request.
"""

from typing import Sequence

import numpy as np
import structlog
from sentence_transformers import SentenceTransformer

from app.core.config import get_settings

logger = structlog.get_logger()
_settings = get_settings()


class LocalEmbeddingModel:
    """Singleton wrapper around a sentence-transformer model."""

    _instance: "LocalEmbeddingModel | None" = None
    _model: SentenceTransformer | None = None
    _model_name: str | None = None

    def __new__(cls) -> "LocalEmbeddingModel":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _load(self) -> SentenceTransformer:
        if self._model is not None:
            return self._model

        primary = _settings.embedding_model
        fallback = _settings.embedding_fallback_model
        device = _settings.embedding_device or "cpu"

        for model_name in (primary, fallback):
            try:
                logger.info("loading_embedding_model", model=model_name, device=device)
                self._model = SentenceTransformer(model_name, device=device)
                self._model_name = model_name
                logger.info("embedding_model_loaded", model=model_name)
                return self._model
            except Exception as exc:
                logger.warning(
                    "embedding_model_load_failed",
                    model=model_name,
                    error=str(exc),
                )

        raise RuntimeError(
            f"Could not load embedding model {primary} or fallback {fallback}"
        )

    @property
    def model_name(self) -> str:
        if self._model_name is None:
            self._load()
        return self._model_name or _settings.embedding_fallback_model

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        """Return L2-normalised embeddings for a list of texts."""
        model = self._load()
        # Strip very long inputs to avoid blowing up memory; 2000 words is plenty
        # for job descriptions.
        cleaned = [str(t)[:12000] for t in texts]
        embeddings = model.encode(
            cleaned,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return np.asarray(embeddings, dtype=np.float32)

    @property
    def dimension(self) -> int:
        model = self._load()
        return model.get_sentence_embedding_dimension()


def get_embedding_model() -> LocalEmbeddingModel:
    return LocalEmbeddingModel()


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Compute cosine similarity between a single vector and a matrix.

    Vectors are assumed to be L2-normalised. Returns values in [-1, 1].
    """
    return np.dot(b, a)
