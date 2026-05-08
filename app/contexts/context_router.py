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
                "history", "story", "journey", "about yourself", "who are you", "childhood", "interests",
                "weather", "school", "college", "university", "class", "study", "job", "career",
                "interview", "work", "advice", "recommend", "should i", "what should i know"],
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
_EVERYDAY_GUIDANCE_TERMS = (
    "weather",
    "school",
    "college",
    "university",
    "class",
    "study",
    "job",
    "career",
    "interview",
    "salary",
    "resume",
    "relocation",
    "sacramento",
    "california",
)
_GUIDANCE_REQUEST_TERMS = (
    "what should",
    "should i",
    "what do i need",
    "what do you recommend",
    "recommend",
    "advice",
    "tips",
    "help me understand",
)
_PERSONAL_PERSPECTIVE_TERMS = (
    "what do you think",
    "what would you",
    "how would you",
    "what are you thinking",
    "your opinion",
    "from your perspective",
)


def is_practical_profile_query(query: str) -> bool:
    """Return whether a query should be answered from persona context."""
    query_lower = query.lower()
    asks_for_guidance = any(term in query_lower for term in _GUIDANCE_REQUEST_TERMS)
    mentions_everyday_topic = any(term in query_lower for term in _EVERYDAY_GUIDANCE_TERMS)
    asks_for_personal_perspective = any(term in query_lower for term in _PERSONAL_PERSPECTIVE_TERMS)
    return mentions_everyday_topic or asks_for_personal_perspective or (
        asks_for_guidance and mentions_everyday_topic
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


def _forced_profile_context(query_lower: str) -> str | None:
    """Route practical life/career/school questions through profile evidence."""
    if is_practical_profile_query(query_lower):
        return "profile"
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
        forced_context = _forced_profile_context(query_lower)
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
