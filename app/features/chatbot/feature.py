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
    "You can help with practical everyday questions related to Patrick's life — "
    "such as weather in Sacramento, traffic conditions, time zones, quick facts, "
    "unit conversions, or simple daily-life questions. "
    "Keep answers short and helpful (1–3 sentences). "
    "You are NOT a general-purpose AI like ChatGPT. "
    "Do NOT write essays, stories, code, long explanations, or help with tasks unrelated to Patrick. "
    "If the user asks something too far outside your scope (e.g. 'write me an essay', "
    "'explain quantum physics', 'help me with my homework'), politely decline and say: "
    "'I'm Patrick's personal assistant — I can help with questions about Patrick or quick everyday topics. "
    "For deeper research, try a general AI tool like ChatGPT.'"
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
