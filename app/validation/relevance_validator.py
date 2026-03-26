"""Validation / reranking layer — decides whether retrieved data truly supports the answer."""

from __future__ import annotations

import logging

from sentence_transformers import CrossEncoder

from app.core.config import get_settings
from app.core.schemas import KnowledgeChunk, RerankResult, RetrievalResult

logger = logging.getLogger(__name__)


class RelevanceValidator:
    """Uses a cross-encoder to rerank candidates and gate irrelevant results."""

    def __init__(self, model_name: str | None = None) -> None:
        model_name = model_name or get_settings().reranker_model
        logger.info("Loading reranker model: %s", model_name)
        self._model = CrossEncoder(model_name)

    def validate(
        self,
        query: str,
        candidates: list[RetrievalResult],
        top_k: int | None = None,
        threshold: float | None = None,
    ) -> list[RerankResult]:
        """Rerank *candidates* and keep only those above *threshold*."""
        if not candidates:
            return []

        settings = get_settings()
        top_k = top_k or settings.rerank_top_k
        threshold = threshold if threshold is not None else settings.relevance_threshold

        pairs = [(query, c.chunk.text) for c in candidates]
        scores = self._model.predict(pairs).tolist()

        scored = [
            RerankResult(chunk=c.chunk, score=s)
            for c, s in zip(candidates, scores)
        ]
        scored.sort(key=lambda r: r.score, reverse=True)

        # Apply threshold and top-k
        filtered = [r for r in scored[:top_k] if r.score >= threshold]
        logger.debug(
            "Reranked %d → %d candidates (threshold=%.2f)",
            len(candidates),
            len(filtered),
            threshold,
        )
        return filtered
