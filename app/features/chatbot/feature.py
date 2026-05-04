"""Chat feature - personal profile Q&A with retrieval-augmented generation."""

from __future__ import annotations

import logging
import re
from collections.abc import AsyncIterator
from typing import Any

from app.core.persona import get_persona_profile, normalize_first_person_answer
from app.core.schemas import AIRequest, RerankResult
from app.features.base import BaseFeature
from app.prompt.prompt_builder import PromptBuilder
from app.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)
_COMPLETE_SENTENCE_RE = re.compile(r"(.+?[.!?])(?:\s+|$)", re.DOTALL)


def _pop_complete_sentences(buffer: str) -> tuple[list[str], str]:
    """Return complete sentence chunks plus unfinished remainder."""
    sentences: list[str] = []
    consumed = 0
    for match in _COMPLETE_SENTENCE_RE.finditer(buffer):
        sentences.append(" ".join(match.group(1).split()))
        consumed = match.end()
    return sentences, buffer[consumed:]


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
        answer = normalize_first_person_answer(answer, request.query)
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
        """Yield normalized answer chunks as soon as each sentence is complete."""
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

        sentence_buffer = ""
        async for token in self._provider.stream_generate(build_result.messages):
            sentence_buffer += token
            sentences, sentence_buffer = _pop_complete_sentences(sentence_buffer)
            for sentence in sentences:
                yield normalize_first_person_answer(sentence, request.query) + " "

        final_sentence = " ".join(sentence_buffer.split())
        if final_sentence:
            yield normalize_first_person_answer(final_sentence, request.query) + " "
