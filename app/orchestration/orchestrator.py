"""Orchestration layer — coordinates the full AI pipeline.

Flow:
  1. Resolve context config
  2. Load knowledge from repository
  3. Retrieve semantically relevant chunks
  4. Validate / rerank with cross-encoder
  5. Delegate to the selected feature service
  6. Return structured response
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from app.contexts.context_registry import ContextRegistry
from app.contexts.context_router import ContextRouter
from app.core.config import get_settings
from app.core.exceptions import ContextNotFoundError, FeatureNotFoundError, ValidationGateError
from app.core.schemas import AIRequest, AIResponse
from app.features.registry import FeatureRegistry
from app.repository.knowledge_repo import KnowledgeRepository
from app.retrieval.embedding_retriever import EmbeddingRetriever
from app.validation.relevance_validator import RelevanceValidator

logger = logging.getLogger(__name__)

_GATE_REFUSAL = (
    "I don't have enough relevant information in my knowledge base to answer "
    "that question. Please ask something related to the topics I know about."
)


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
    ) -> None:
        self._contexts = context_registry
        self._features = feature_registry
        self._repo = knowledge_repo
        self._retriever = retriever
        self._validator = validator
        self._context_router = context_router

    # ── shared pipeline steps ─────────────────────────────────────────

    async def _resolve(self, request: AIRequest):
        """Run the common resolve → retrieve → validate pipeline.

        Returns (context_config, feature, validated_chunks, retrieval_count).
        """
        ctx = self._contexts.get(request.context)
        if ctx is None:
            raise ContextNotFoundError(request.context)

        feature = self._features.get(request.feature)
        if feature is None:
            raise FeatureNotFoundError(request.feature)

        user_id: str | None = request.options.get("user_id")
        chunks = await self._repo.get_chunks(request.context, user_id=user_id)
        retrieved = self._retriever.retrieve(request.query, chunks)
        validated = self._validator.validate(request.query, retrieved)

        if not validated:
            logger.warning("No relevant data after validation gate for query: %s", request.query)

        return ctx, feature, validated, len(retrieved)

    # ── standard (non-streaming) ──────────────────────────────────────

    async def handle(self, request: AIRequest) -> AIResponse:
        ctx, feature, validated, retrieved_count = await self._resolve(request)

        # ── relevance gate ────────────────────────────────────────────
        if not validated and get_settings().relevance_gate_enabled:
            logger.info("Relevance gate BLOCKED query (no supporting chunks): %s", request.query[:120])
            key = "answer" if request.feature == "chat" else "result"
            return AIResponse(
                success=True,
                data={key: _GATE_REFUSAL, "supported": False},
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
            extra_rules=ctx.extra_rules,
        )

        return AIResponse(
            success=True,
            data=data,
            meta={
                "feature": request.feature,
                "context": request.context,
                "chunks_retrieved": retrieved_count,
                "chunks_validated": len(validated),
            },
        )

    async def detect_context(self, query: str) -> str:
        """Return the best-matching context name for *query* (falls back to 'general')."""
        if self._context_router is None:
            return "general"
        return await self._context_router.route(query)

    def check_request(self, request: AIRequest) -> None:
        """Eagerly validate context and feature; raises ContextNotFoundError / FeatureNotFoundError."""
        # 'auto' is always valid — it will be resolved before the pipeline runs
        if request.context != "auto" and self._contexts.get(request.context) is None:
            raise ContextNotFoundError(request.context)
        if self._features.get(request.feature) is None:
            raise FeatureNotFoundError(request.feature)

    # ── streaming (SSE) ───────────────────────────────────────────────

    async def handle_stream(self, request: AIRequest) -> AsyncIterator[str]:
        """Run the pipeline then yield text tokens from the feature's stream_execute."""
        ctx, feature, validated, _ = await self._resolve(request)

        # ── relevance gate ────────────────────────────────────────────
        if not validated and get_settings().relevance_gate_enabled:
            logger.info("Relevance gate BLOCKED stream query: %s", request.query[:120])
            yield _GATE_REFUSAL
            return

        async for token in feature.stream_execute(
            request,
            validated,
            system_instruction=ctx.system_instruction,
            output_style=ctx.output_style,
            extra_rules=ctx.extra_rules,
        ):
            yield token
