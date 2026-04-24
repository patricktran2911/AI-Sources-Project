"""Context auto-router — infers the best knowledge context for a query."""

from __future__ import annotations

import logging

from app.contexts.context_registry import ContextRegistry
from app.repository.knowledge_repo import KnowledgeRepository
from app.retrieval.embedding_retriever import EmbeddingRetriever

logger = logging.getLogger(__name__)

_FALLBACK = "general"

# Keyword hints that boost a context's routing score by 20 % when matched.
_KEYWORD_HINTS: dict[str, list[str]] = {
    "projects": ["project", "built", "build", "created", "developed", "application", "app", "system"],
    "portfolio": ["portfolio", "published", "launched", "released", "showcase", "app store"],
    "profile": ["hire", "contact", "email", "linkedin", "skill", "experience", "background",
                "education", "degree", "availability", "salary", "work history", "resume", "cv",
                "history", "story", "journey", "about yourself", "who are you", "childhood", "interests"],
}
_BOOST = 2.0  # 2× score boost when keywords match — needed to overcome large-context bias


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

    async def route(self, query: str) -> str:
        """Return the context name that best matches *query*."""
        # Score every context except the fallback itself
        candidates = [n for n in self._contexts.list_names() if n != _FALLBACK]

        best_context = _FALLBACK
        best_score = -1.0

        for name in candidates:
            chunks = await self._repo.get_chunks(name)
            if not chunks:
                continue
            results = self._retriever.retrieve(query, chunks, top_k=3)
            if not results:
                continue
            # Mean of top-3 scores — normalises for context size so a context with
            # 47 chunks does not unfairly beat one with 15 just from raw chunk count.
            score = sum(r.score for r in results) / len(results)
            # Keyword boost: if the query contains hint words for this context,
            # amplify its score to break ties in favour of the most-specific context.
            query_lower = query.lower()
            if any(kw in query_lower for kw in _KEYWORD_HINTS.get(name, [])):
                score *= _BOOST
            if score > best_score:
                best_score = score
                best_context = name

        logger.info(
            "Auto-routed query to context '%s' (sum_score=%.3f)", best_context, best_score
        )
        return best_context
