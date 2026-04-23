"""Keyword-based retrieval using BM25 (Okapi BM25)."""

from __future__ import annotations

import logging
import re

from rank_bm25 import BM25Okapi

from app.core.config import get_settings
from app.core.schemas import KnowledgeChunk, RetrievalResult

logger = logging.getLogger(__name__)

_SPLIT_RE = re.compile(r"\W+")


def _tokenize(text: str) -> list[str]:
    """Lowercase whitespace/punctuation split — fast and language-agnostic."""
    return [t for t in _SPLIT_RE.split(text.lower()) if t]


class BM25Retriever:
    """Sparse keyword retrieval via Okapi BM25.

    Complements the dense embedding retriever by catching exact keyword matches
    that dense models sometimes miss (e.g. proper nouns, acronyms, versions).
    """

    def retrieve(
        self,
        query: str,
        chunks: list[KnowledgeChunk],
        top_k: int | None = None,
    ) -> list[RetrievalResult]:
        """Return the top-k chunks most relevant to *query* by BM25 score."""
        if not chunks:
            return []

        top_k = top_k or get_settings().retrieval_top_k

        tokenized_corpus = [_tokenize(c.text) for c in chunks]
        bm25 = BM25Okapi(tokenized_corpus)

        query_tokens = _tokenize(query)
        scores = bm25.get_scores(query_tokens)

        top_indices = scores.argsort()[::-1][:top_k]

        results = [
            RetrievalResult(chunk=chunks[int(i)], score=float(scores[i]))
            for i in top_indices
            if scores[i] > 0.0
        ]
        logger.debug("BM25 retrieved %d chunks (top score %.3f)", len(results), results[0].score if results else 0)
        return results
