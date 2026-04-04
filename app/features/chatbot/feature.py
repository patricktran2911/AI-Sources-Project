"""Chat feature — personal profile Q&A with retrieval-augmented generation."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from app.core.schemas import AIRequest, RerankResult
from app.features.base import BaseFeature
from app.prompt.prompt_builder import PromptBuilder
from app.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)

_NO_DATA_ANSWER = (
    "I don't have enough relevant information in my knowledge base to answer that question. "
    "Please ask something related to the topics I know about."
)


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
        **kwargs,
    ) -> dict[str, Any]:
        history: list[dict[str, str]] = request.options.get("history", [])

        # No relevant knowledge chunks — return canned refusal (no LLM call)
        if not context_data:
            logger.info("Chat gate: no relevant chunks, refusing query '%s'", request.query)
            return {"answer": _NO_DATA_ANSWER, "supported": False}

        messages = self._prompt_builder.build(
            query=request.query,
            validated_chunks=context_data,
            system_instruction=system_instruction,
            output_style=output_style,
            extra_rules=extra_rules,
            history=history,
        )

        answer = await self._provider.generate(messages)
        return {"answer": answer, "supported": True}

    async def stream_execute(
        self,
        request: AIRequest,
        context_data: list[RerankResult],
        *,
        system_instruction: str = "",
        output_style: str = "concise and professional",
        extra_rules: list[str] | None = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Yield answer tokens one chunk at a time for SSE streaming."""
        history: list[dict[str, str]] = request.options.get("history", [])

        # No relevant knowledge chunks — return canned refusal (no LLM call)
        if not context_data:
            logger.info("Chat stream gate: no relevant chunks, refusing query '%s'", request.query)
            yield _NO_DATA_ANSWER
            return

        messages = self._prompt_builder.build(
            query=request.query,
            validated_chunks=context_data,
            system_instruction=system_instruction,
            output_style=output_style,
            extra_rules=extra_rules,
            history=history,
        )

        async for token in self._provider.stream_generate(messages):
            yield token
