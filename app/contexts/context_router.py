"""Context auto-router - infers the best knowledge context for a query."""

from __future__ import annotations

import logging

from app.contexts.context_registry import ContextRegistry
from app.repository.knowledge_repo import KnowledgeRepository
from app.retrieval.embedding_retriever import EmbeddingRetriever

logger = logging.getLogger(__name__)

_FALLBACK = "general"

# Keyword hints that boost a context's routing score when matched.
_KEYWORD_HINTS: dict[str, list[str]] = {
    "projects": ["project", "built", "build", "created", "developed", "application", "app", "system"],
    "portfolio": ["portfolio", "published", "launched", "released", "showcase", "app store"],
    "profile": ["hire", "contact", "email", "linkedin", "skill", "experience", "background",
                "education", "degree", "availability", "salary", "work history", "resume", "cv",
                "history", "story", "journey", "about yourself", "who are you", "childhood", "interests"],
}
_BOOST = 2.0  # 2x score boost when keywords match to overcome large-context bias
_PROJECT_COMPARISON_PHRASES = (
    "which project",
    "best project",
    "strongest project",
    "favorite project",
)
_PROJECT_EVALUATION_TERMS = (
    "best",
    "strongest",
    "show",
    "shows",
    "showcase",
    "showcases",
    "demonstrate",
    "demonstrates",
    "highlight",
    "highlights",
    "represent",
    "represents",
)
_PROJECT_SKILL_TERMS = (
    "product",
    "engineering",
    "engineer",
    "skill",
    "skills",
    "technical",
)


def _forced_context(query_lower: str) -> str | None:
    """Return a context override for especially explicit query wording."""
    mentions_project = "project" in query_lower or "projects" in query_lower
    if not mentions_project:
        return None

    if any(phrase in query_lower for phrase in _PROJECT_COMPARISON_PHRASES):
        return "projects"

    asks_for_project_judgment = any(term in query_lower for term in _PROJECT_EVALUATION_TERMS)
    asks_about_skills = any(term in query_lower for term in _PROJECT_SKILL_TERMS)
    if asks_for_project_judgment and asks_about_skills:
        return "projects"

    return None


class ContextRouter:
    """Selects the most relevant context for a query using embedding similarity.

    For each registered context it retrieves the top-3 chunks and uses the
    average cosine similarity score as the signal. The context with the best
    overall score wins; ``general`` is used as a hard fallback.
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
        query_lower = query.lower()
        forced_context = _forced_context(query_lower)
        if forced_context is not None:
            logger.info("Auto-routed query to forced context '%s'", forced_context)
            return forced_context

        candidates = [name for name in self._contexts.list_names() if name != _FALLBACK]
        best_context = _FALLBACK
        best_score = -1.0

        for name in candidates:
            chunks = await self._repo.get_chunks(name)
            if not chunks:
                continue

            results = self._retriever.retrieve(query, chunks, top_k=3)
            if not results:
                continue

            score = sum(result.score for result in results) / len(results)
            if any(keyword in query_lower for keyword in _KEYWORD_HINTS.get(name, [])):
                score *= _BOOST

            if score > best_score:
                best_score = score
                best_context = name

        logger.info("Auto-routed query to context '%s' (score=%.3f)", best_context, best_score)
        return best_context
