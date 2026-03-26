"""Context auto-router — infers the best knowledge context for a query."""

from __future__ import annotations

import logging

from app.contexts.context_registry import ContextRegistry
from app.repository.knowledge_repo import KnowledgeRepository
from app.retrieval.embedding_retriever import EmbeddingRetriever

logger = logging.getLogger(__name__)

_FALLBACK = "general"


class ContextRouter:
    """Selects the most relevant context for a query using embedding similarity.

    For each registered context it retrieves the top-3 chunks and uses the
    highest cosine-similarity score as the signal.  The context with the
    overall best score wins; ``general`` is used as a hard fallback.
    """

    def __init__(
        self,
        context_registry: ContextRegistry,
        knowledge_repo: KnowledgeRepository,
        retriever: EmbeddingRetriever,
    ) -> None:
        self._contexts = context_registry
        self._repo = knowledge_repo
        self._retriever = retriever

    def route(self, query: str) -> str:
        """Return the context name that best matches *query*."""
        # Score every context except the fallback itself
        candidates = [n for n in self._contexts.list_names() if n != _FALLBACK]

        best_context = _FALLBACK
        best_score = -1.0

        for name in candidates:
            chunks = self._repo.get_chunks(name)
            if not chunks:
                continue
            results = self._retriever.retrieve(query, chunks, top_k=3)
            if results and results[0].score > best_score:
                best_score = results[0].score
                best_context = name

        logger.info(
            "Auto-routed query to context '%s' (score=%.3f)", best_context, best_score
        )
        return best_context
