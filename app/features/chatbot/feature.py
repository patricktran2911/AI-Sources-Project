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

_GENERAL_SYSTEM = (
    "You are Patrick Tran's personal AI assistant. "
    "Patrick Tran is also known as Phúc, Nguyên, Nguyen, Bin, or Bin đầu bạc — all these names refer to the same person. "
    "You are friendly and helpful. "
    "Your primary focus is answering questions about Patrick — his background, skills, projects, experience, and daily life. "
    "You can also help with practical everyday questions such as weather, time zones, quick facts, or simple daily-life topics. "
    "If a question is not directly about Patrick, still do your best to give a brief, helpful answer. "
    "Keep answers short and helpful (1–4 sentences). "
    "Only decline if the request is clearly inappropriate or harmful."
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

        # No relevant knowledge chunks — fall back to plain GPT as a general assistant
        if not context_data:
            logger.info("Chat gate: no relevant chunks, using general fallback for query '%s'", request.query)
            messages = self._prompt_builder.build(
                query=request.query,
                validated_chunks=[],
                system_instruction=_GENERAL_SYSTEM,
                history=history,
            )
            answer = await self._provider.generate(messages)
            return {"answer": answer, "supported": False}

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

        # No relevant knowledge chunks — fall back to plain GPT as a general assistant
        if not context_data:
            logger.info("Chat stream gate: no relevant chunks, using general fallback for query '%s'", request.query)
            messages = self._prompt_builder.build(
                query=request.query,
                validated_chunks=[],
                system_instruction=_GENERAL_SYSTEM,
                history=history,
            )
            async for token in self._provider.stream_generate(messages):
                yield token
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
