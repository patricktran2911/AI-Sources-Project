"""Suggest feature — generates recommendations based on retrieved context."""

from __future__ import annotations

import logging
from typing import Any

from app.core.schemas import AIRequest, RerankResult
from app.features.base import BaseFeature
from app.prompt.prompt_builder import PromptBuilder
from app.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class SuggestFeature(BaseFeature):
    name = "suggest"

    def __init__(self, provider: BaseLLMProvider, prompt_builder: PromptBuilder) -> None:
        self._provider = provider
        self._prompt_builder = prompt_builder

    async def execute(
        self,
        request: AIRequest,
        context_data: list[RerankResult],
        *,
        system_instruction: str = "",
        output_style: str = "actionable suggestions",
        extra_rules: list[str] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        rules = list(extra_rules or [])
        rules.append("Provide actionable, ranked suggestions based on the supporting information.")

        messages = self._prompt_builder.build(
            query=request.query,
            validated_chunks=context_data,
            system_instruction=system_instruction,
            output_style=output_style,
            extra_rules=rules,
        )

        answer = await self._provider.generate(messages)
        return {"result": answer}
