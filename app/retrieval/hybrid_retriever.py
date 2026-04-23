"""Hybrid retriever — fuses dense embedding + BM25 scores, then applies MMR."""

from __future__ import annotations

import logging

import numpy as np

from app.core.config import get_settings
from app.core.schemas import KnowledgeChunk, RetrievalResult
from app.retrieval.bm25_retriever import BM25Retriever
from app.retrieval.embedding_retriever import EmbeddingRetriever

logger = logging.getLogger(__name__)


def _min_max_normalise(scores: dict[str, float]) -> dict[str, float]:
    """Normalise a dict of scores to [0, 1]."""
    if not scores:
        return scores
    vals = list(scores.values())
    lo, hi = min(vals), max(vals)
    rng = hi - lo
    if rng == 0:
        return {k: 1.0 for k in scores}
    return {k: (v - lo) / rng for k, v in scores.items()}


class HybridRetriever:
    """Combines dense embedding retrieval with BM25 keyword retrieval.

    Flow:
        1. Both retrievers score all chunks independently.
        2. Scores are min-max normalised per retriever.
        3. Weighted fusion: ``dense_weight × dense + (1 - dense_weight) × bm25``.
        4. Top-k by fused score.
        5. (Optional) MMR diversification via ``EmbeddingRetriever.mmr_select``.
    """

    def __init__(
        self,
        embedding_retriever: EmbeddingRetriever,
        bm25_retriever: BM25Retriever | None = None,
        dense_weight: float = 0.6,
        use_mmr: bool = True,
        mmr_lambda: float = 0.7,
    ) -> None:
        self._dense = embedding_retriever
        self._sparse = bm25_retriever or BM25Retriever()
        self._dense_weight = dense_weight
        self._use_mmr = use_mmr
        self._mmr_lambda = mmr_lambda

    def retrieve(
        self,
        query: str,
        chunks: list[KnowledgeChunk],
        top_k: int | None = None,
    ) -> list[RetrievalResult]:
        """Return top-k chunks using hybrid dense + BM25 fusion."""
        if not chunks:
            return []

        settings = get_settings()
        top_k = top_k or settings.retrieval_top_k

        # --- score with both retrievers (full candidate pool) ---
        dense_results = self._dense.retrieve(query, chunks, top_k=len(chunks))
        sparse_results = self._sparse.retrieve(query, chunks, top_k=len(chunks))

        dense_scores = _min_max_normalise({r.chunk.id: r.score for r in dense_results})
        sparse_scores = _min_max_normalise({r.chunk.id: r.score for r in sparse_results})

        all_ids = set(dense_scores) | set(sparse_scores)
        chunk_map = {c.id: c for c in chunks}

        fused: list[RetrievalResult] = []
        for cid in all_ids:
            d = dense_scores.get(cid, 0.0)
            s = sparse_scores.get(cid, 0.0)
            score = self._dense_weight * d + (1 - self._dense_weight) * s
            fused.append(RetrievalResult(chunk=chunk_map[cid], score=score))

        fused.sort(key=lambda r: r.score, reverse=True)
        top_results = fused[:top_k]

        # --- optional MMR diversification ---
        if self._use_mmr and len(top_results) > 1:
            query_emb = self._dense.encode_query(query)
            candidate_embs = np.array([
                self._dense.get_embedding(r.chunk.text) for r in top_results
            ])
            top_results = EmbeddingRetriever.mmr_select(
                query_emb, top_results, candidate_embs,
                top_k=top_k, lambda_param=self._mmr_lambda,
            )

        logger.debug(
            "Hybrid retrieved %d chunks (dense_w=%.1f, mmr=%s)",
            len(top_results), self._dense_weight, self._use_mmr,
        )
        return top_results
