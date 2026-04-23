"""Semantic retrieval using sentence-transformers embeddings."""

from __future__ import annotations

import hashlib
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
    """Encode queries and chunks with a sentence-transformer, retrieve by cosine similarity.

    Chunk embeddings are cached by content hash so they are only computed once
    per unique text, regardless of how many requests arrive.
    """

    def __init__(self, model_name: str | None = None) -> None:
        model_name = model_name or get_settings().embedding_model
        logger.info("Loading embedding model: %s", model_name)
        self._model = SentenceTransformer(model_name)
        self._cache: dict[str, np.ndarray] = {}

    # ── public API ────────────────────────────────────────────────────

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

        chunk_embs = self._get_chunk_embeddings(chunks)
        query_emb = self._model.encode([query], normalize_embeddings=True)

        scores = np.dot(chunk_embs, query_emb.T).flatten()
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = [
            RetrievalResult(chunk=chunks[i], score=float(scores[i]))
            for i in top_indices
        ]
        logger.debug("Retrieved %d chunks (top score %.3f)", len(results), results[0].score if results else 0)
        return results

    def encode_query(self, query: str) -> np.ndarray:
        """Return the normalised embedding for a single query string."""
        return self._model.encode([query], normalize_embeddings=True)[0]

    def get_embedding(self, text: str) -> np.ndarray:
        """Return cached normalised embedding for an arbitrary text."""
        key = self._hash(text)
        if key not in self._cache:
            self._cache[key] = self._model.encode([text], normalize_embeddings=True)[0]
        return self._cache[key]

    # ── MMR diversification ───────────────────────────────────────────

    @staticmethod
    def mmr_select(
        query_emb: np.ndarray,
        candidates: list[RetrievalResult],
        candidate_embs: np.ndarray,
        top_k: int = 5,
        lambda_param: float = 0.7,
    ) -> list[RetrievalResult]:
        """Select *top_k* results via Maximal Marginal Relevance.

        ``lambda_param`` balances relevance (1.0) vs. diversity (0.0).
        """
        if len(candidates) <= top_k:
            return candidates

        query_emb = query_emb.flatten()
        selected_indices: list[int] = []
        remaining = list(range(len(candidates)))

        for _ in range(top_k):
            best_idx = -1
            best_mmr = -np.inf
            for idx in remaining:
                relevance = float(np.dot(candidate_embs[idx], query_emb))
                if selected_indices:
                    sel_embs = candidate_embs[selected_indices]
                    max_sim = float(np.max(np.dot(sel_embs, candidate_embs[idx])))
                else:
                    max_sim = 0.0
                mmr = lambda_param * relevance - (1 - lambda_param) * max_sim
                if mmr > best_mmr:
                    best_mmr = mmr
                    best_idx = idx
            if best_idx < 0:
                break
            selected_indices.append(best_idx)
            remaining.remove(best_idx)

        return [candidates[i] for i in selected_indices]

    # ── internal helpers ──────────────────────────────────────────────

    def _get_chunk_embeddings(self, chunks: list[KnowledgeChunk]) -> np.ndarray:
        """Return a (N, dim) array of embeddings, using cache where possible."""
        uncached_indices: list[int] = []
        uncached_texts: list[str] = []
        keys = [self._hash(c.text) for c in chunks]

        for i, key in enumerate(keys):
            if key not in self._cache:
                uncached_indices.append(i)
                uncached_texts.append(chunks[i].text)

        if uncached_texts:
            new_embs = self._model.encode(uncached_texts, normalize_embeddings=True)
            for j, idx in enumerate(uncached_indices):
                self._cache[keys[idx]] = new_embs[j]

        return np.array([self._cache[k] for k in keys])

    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()
