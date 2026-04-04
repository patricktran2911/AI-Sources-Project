"""Summarize feature — condenses retrieved information into a summary."""

from __future__ import annotations

import logging
from typing import Any

from app.core.schemas import AIRequest, RerankResult
from app.features.base import BaseFeature
from app.prompt.prompt_builder import PromptBuilder
from app.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class SummarizeFeature(BaseFeature):
    name = "summarize"

    def __init__(self, provider: BaseLLMProvider, prompt_builder: PromptBuilder) -> None:
        self._provider = provider
        self._prompt_builder = prompt_builder

    async def execute(
        self,
        request: AIRequest,
        context_data: list[RerankResult],
        *,
        system_instruction: str = "",
        output_style: str = "concise summary",
        extra_rules: list[str] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        if not context_data:
            return {"result": "No relevant knowledge found to summarise.", "supported": False}

        rules = list(extra_rules or [])
        rules.append("Produce a clear, structured summary of the supporting information.")

        messages = self._prompt_builder.build(
            query=request.query,
            validated_chunks=context_data,
            system_instruction=system_instruction,
            output_style=output_style,
            extra_rules=rules,
        )

        answer = await self._provider.generate(messages)
        return {"result": answer}
