"""Prompt builder — assembles compact prompts for the external LLM."""

from __future__ import annotations

import logging
from typing import Any

from app.core.schemas import RerankResult

logger = logging.getLogger(__name__)

_LANGUAGE_RULE = (
    "Always detect the language of the user's question and respond in that exact same language."
)


class PromptBuilder:
    """Build clean, context-aware prompts from validated data and context rules."""

    def build(
        self,
        query: str,
        validated_chunks: list[RerankResult],
        system_instruction: str,
        output_style: str = "concise and helpful",
        extra_rules: list[str] | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> list[dict[str, str]]:
        """Return an OpenAI-style messages list (system + optional history + user).

        The builder compacts supporting evidence into the user message so the
        external LLM receives only what it needs.
        """
        evidence = self._format_evidence(validated_chunks)

        system_parts = [system_instruction]
        if extra_rules:
            system_parts.extend(extra_rules)
        system_parts.append(f"Response style: {output_style}.")
        system_parts.append(_LANGUAGE_RULE)
        system_msg = "\n".join(system_parts)

        if evidence:
            user_msg = (
                f"Supporting information:\n{evidence}\n\n"
                f"User question:\n{query}"
            )
        else:
            user_msg = query

        messages: list[dict[str, str]] = [{"role": "system", "content": system_msg}]

        # Inject prior conversation turns before the current message
        if history:
            messages.extend(history)

        messages.append({"role": "user", "content": user_msg})
        logger.debug("Built prompt with %d system chars, %d user chars, %d history turns",
                     len(system_msg), len(user_msg), len(history) if history else 0)
        return messages

    @staticmethod
    def _format_evidence(chunks: list[RerankResult]) -> str:
        if not chunks:
            return ""
        lines: list[str] = []
        for i, r in enumerate(chunks, 1):
            lines.append(f"[{i}] {r.chunk.text}")
        return "\n".join(lines)
