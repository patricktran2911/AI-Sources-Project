"""Chat feature - personal profile Q&A with retrieval-augmented generation."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from app.core.persona import get_persona_profile
from app.core.schemas import AIRequest, RerankResult
from app.features.base import BaseFeature
from app.prompt.prompt_builder import PromptBuilder
from app.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class ChatFeature(BaseFeature):
    name = "chat"

    def __init__(self, provider: BaseLLMProvider, prompt_builder: PromptBuilder) -> None:
        self._provider = provider
        self._prompt_builder = prompt_builder

    async def execute(
        self,
        request: AIRequest,
        context_data: list[RerankResult],
        *,
        system_instruction: str = "",
        output_style: str = "concise and professional",
        extra_rules: list[str] | None = None,
        max_context_tokens: int | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        history: list[dict[str, str]] = request.options.get("history", [])
        refusal_message = get_persona_profile().refusal_message

        if not context_data:
            logger.info("Chat gate: no relevant chunks, refusing query '%s'", request.query)
            return {"answer": refusal_message, "supported": False}

        build_result = self._prompt_builder.build(
            query=request.query,
            validated_chunks=context_data,
            system_instruction=system_instruction,
            output_style=output_style,
            extra_rules=extra_rules,
            history=history,
            max_context_tokens=max_context_tokens,
        )
        request.options["_prompt_budget"] = build_result.metrics.as_meta()

        answer = await self._provider.generate(build_result.messages)
        return {
            "answer": answer,
            "supported": True,
            "budget": build_result.metrics.as_meta(),
        }

    async def stream_execute(
        self,
        request: AIRequest,
        context_data: list[RerankResult],
        *,
        system_instruction: str = "",
        output_style: str = "concise and professional",
        extra_rules: list[str] | None = None,
        max_context_tokens: int | None = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Yield answer tokens one chunk at a time for SSE streaming."""
        history: list[dict[str, str]] = request.options.get("history", [])
        refusal_message = get_persona_profile().refusal_message

        if not context_data:
            logger.info("Chat stream gate: no relevant chunks, refusing query '%s'", request.query)
            yield refusal_message
            return

        build_result = self._prompt_builder.build(
            query=request.query,
            validated_chunks=context_data,
            system_instruction=system_instruction,
            output_style=output_style,
            extra_rules=extra_rules,
            history=history,
            max_context_tokens=max_context_tokens,
        )
        request.options["_prompt_budget"] = build_result.metrics.as_meta()

        async for token in self._provider.stream_generate(build_result.messages):
            yield token
