"""Orchestration layer - coordinates the full AI pipeline.

Flow:
  1. Validate the request against local guardrails.
  2. Resolve context config.
  3. Load knowledge from repository.
  4. Enrich the retrieval query with recent conversation history.
  5. Retrieve relevant chunks (hybrid dense + BM25 when available).
  6. Validate / rerank with the cross-encoder.
  7. Delegate to the chat feature.
  8. Return structured response metadata.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from app.contexts.context_registry import ContextRegistry
from app.contexts.context_router import ContextRouter
from app.contexts.intent_classifier import INTENT_PROMPT_HINTS, classify_intent
from app.core.config import get_settings
from app.core.exceptions import ContextNotFoundError, FeatureNotFoundError
from app.core.persona import get_persona_profile
from app.core.schemas import AIRequest, AIResponse
from app.features.registry import FeatureRegistry
from app.orchestration.query_guard import guard_query
from app.repository.knowledge_repo import KnowledgeRepository
from app.retrieval.embedding_retriever import EmbeddingRetriever
from app.retrieval.hybrid_retriever import HybridRetriever
from app.validation.relevance_validator import RelevanceValidator

logger = logging.getLogger(__name__)


class Orchestrator:
    """Single entry point for all incoming AI requests."""

    def __init__(
        self,
        context_registry: ContextRegistry,
        feature_registry: FeatureRegistry,
        knowledge_repo: KnowledgeRepository,
        retriever: EmbeddingRetriever,
        validator: RelevanceValidator,
        context_router: ContextRouter | None = None,
        hybrid_retriever: HybridRetriever | None = None,
    ) -> None:
        self._contexts = context_registry
        self._features = feature_registry
        self._repo = knowledge_repo
        self._retriever = retriever
        self._validator = validator
        self._context_router = context_router
        self._hybrid = hybrid_retriever

    @staticmethod
    def _enrich_query(query: str, history: list[dict[str, str]]) -> str:
        """Prepend recent conversation context to the retrieval query."""
        if not history:
            return query

        prior_user_msgs = [message["content"] for message in history if message["role"] == "user"]
        if not prior_user_msgs:
            return query

        last_user = prior_user_msgs[-1]
        if len(last_user) > 200:
            last_user = last_user[:200]
        return f"{last_user} {query}"

    async def _resolve(self, request: AIRequest):
        """Run the common resolve -> retrieve -> validate pipeline."""
        ctx = self._contexts.get(request.context)
        if ctx is None:
            raise ContextNotFoundError(request.context)

        feature = self._features.get(request.feature)
        if feature is None:
            raise FeatureNotFoundError(request.feature)

        user_id: str | None = request.options.get("user_id")
        chunks = await self._repo.get_chunks(request.context, user_id=user_id)

        history: list[dict[str, str]] = request.options.get("history", [])
        retrieval_query = self._enrich_query(request.query, history)

        if self._hybrid is not None:
            retrieved = self._hybrid.retrieve(retrieval_query, chunks)
        else:
            retrieved = self._retriever.retrieve(retrieval_query, chunks)

        validated = self._validator.validate(request.query, retrieved)

        if not validated:
            logger.warning("No relevant data after validation gate for query: %s", request.query)

        return ctx, feature, validated, len(retrieved)

    @staticmethod
    def _build_rules(query: str, ctx_rules: list[str] | None) -> list[str]:
        """Merge context-level extra rules with an intent-specific hint."""
        rules = list(ctx_rules) if ctx_rules else []
        intent = classify_intent(query)
        hint = INTENT_PROMPT_HINTS.get(intent)
        if hint:
            rules.append(hint)
        return rules

    @staticmethod
    def _build_guard_meta(request: AIRequest, reason: str) -> dict[str, Any]:
        return {
            "feature": request.feature,
            "context": request.context,
            "chunks_retrieved": 0,
            "chunks_validated": 0,
            "guarded": True,
            "guard_reason": reason,
        }

    async def handle(self, request: AIRequest) -> AIResponse:
        guard = guard_query(request.query)
        if guard.blocked:
            logger.info("Query guard blocked request: %s", guard.reason)
            return AIResponse(
                success=True,
                data={"answer": guard.response or get_persona_profile().refusal_message, "supported": False},
                meta=self._build_guard_meta(request, guard.reason or "blocked"),
            )

        ctx, feature, validated, retrieved_count = await self._resolve(request)

        if not validated and get_settings().relevance_gate_enabled:
            logger.info("Relevance gate blocked query (no supporting chunks): %s", request.query[:120])
            return AIResponse(
                success=True,
                data={"answer": get_persona_profile().refusal_message, "supported": False},
                meta={
                    "feature": request.feature,
                    "context": request.context,
                    "chunks_retrieved": retrieved_count,
                    "chunks_validated": 0,
                    "gated": True,
                },
            )

        data = await feature.execute(
            request,
            validated,
            system_instruction=ctx.system_instruction,
            output_style=ctx.output_style,
            extra_rules=self._build_rules(request.query, ctx.extra_rules),
            max_context_tokens=ctx.max_context_tokens,
        )

        prompt_budget = data.pop("budget", None)
        meta: dict[str, Any] = {
            "feature": request.feature,
            "context": request.context,
            "chunks_retrieved": retrieved_count,
            "chunks_validated": len(validated),
        }
        if prompt_budget:
            meta["prompt_budget"] = prompt_budget

        return AIResponse(success=True, data=data, meta=meta)

    async def detect_context(self, query: str) -> str:
        """Return the best-matching context name for query."""
        if self._context_router is None:
            return "general"
        return await self._context_router.route(query)

    def check_request(self, request: AIRequest) -> None:
        """Eagerly validate context and feature names."""
        if request.context != "auto" and self._contexts.get(request.context) is None:
            raise ContextNotFoundError(request.context)
        if self._features.get(request.feature) is None:
            raise FeatureNotFoundError(request.feature)

    async def handle_stream(self, request: AIRequest) -> AsyncIterator[str]:
        """Run the pipeline then yield text tokens from the feature's stream_execute."""
        guard = guard_query(request.query)
        if guard.blocked:
            logger.info("Query guard blocked stream request: %s", guard.reason)
            request.options["_stream_meta"] = {
                "supported": False,
                "guarded": True,
                "guard_reason": guard.reason,
            }
            yield guard.response or get_persona_profile().refusal_message
            return

        ctx, feature, validated, _ = await self._resolve(request)

        if not validated and get_settings().relevance_gate_enabled:
            logger.info("Relevance gate blocked stream query: %s", request.query[:120])
            request.options["_stream_meta"] = {"supported": False, "gated": True}
            yield get_persona_profile().refusal_message
            return

        request.options["_stream_meta"] = {"supported": True}
        async for token in feature.stream_execute(
            request,
            validated,
            system_instruction=ctx.system_instruction,
            output_style=ctx.output_style,
            extra_rules=self._build_rules(request.query, ctx.extra_rules),
            max_context_tokens=ctx.max_context_tokens,
        ):
            yield token
