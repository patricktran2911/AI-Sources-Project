"""Semantic retrieval using sentence-transformers embeddings."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import get_settings
from app.core.schemas import KnowledgeChunk, RetrievalResult

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class EmbeddingRetriever:
    """Encode queries and chunks with a sentence-transformer, retrieve by cosine similarity."""

    def __init__(self, model_name: str | None = None) -> None:
        model_name = model_name or get_settings().embedding_model
        logger.info("Loading embedding model: %s", model_name)
        self._model = SentenceTransformer(model_name)

    def retrieve(
        self,
        query: str,
        chunks: list[KnowledgeChunk],
        top_k: int | None = None,
    ) -> list[RetrievalResult]:
        """Return the top-k chunks most similar to *query*."""
        if not chunks:
            return []

        settings = get_settings()
        top_k = top_k or settings.retrieval_top_k

        texts = [c.text for c in chunks]
        query_emb = self._model.encode([query], normalize_embeddings=True)
        chunk_embs = self._model.encode(texts, normalize_embeddings=True)

        scores = np.dot(chunk_embs, query_emb.T).flatten()
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = [
            RetrievalResult(chunk=chunks[i], score=float(scores[i]))
            for i in top_indices
        ]
        logger.debug("Retrieved %d chunks (top score %.3f)", len(results), results[0].score if results else 0)
        return results
