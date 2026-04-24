"""Prompt builder - assembles compact prompts for the external LLM."""

from __future__ import annotations

import logging

from app.core.persona import get_persona_profile
from app.core.schemas import RerankResult
from app.prompt.prompt_budget import PromptBuildResult, PromptBudget, PromptMetrics, estimate_message_tokens

logger = logging.getLogger(__name__)

_LANGUAGE_RULE = (
    "Always detect the language of the user's question and respond in that same language."
)

_BREVITY_RULE = (
    "Be concise. Answer in 1-3 sentences unless the user explicitly asks for detail or a list."
)

_VOICE_RULE = (
    "Write like a real person, not a generic AI assistant. "
    "Prefer natural first-person phrasing when speaking on behalf of the persona, "
    "use contractions when they sound natural, and avoid robotic filler, buzzwords, or repeated hedging. "
    "Do not tack on generic assistant closers like 'How can I assist you?' unless the user explicitly asks for help "
    "or the conversation naturally calls for it."
)

_GROUNDING_RULE = (
    "Base your answer strictly on the Supporting Information provided. "
    "Do not invent facts or add information that is not present in the evidence. "
    "If the supporting information is insufficient to answer fully, clearly state what you can confirm "
    "and what you cannot."
)

_SCOPE_RULE = (
    "You are strictly a personal AI assistant for the configured persona. "
    "The allowed scope includes the person's life story, personal history, background, education, work, projects, "
    "interests, location, contact details, preferences, and any other approved information grounded in the evidence. "
    "Refuse to answer questions that are not about that person or not supported by approved information about them. "
    "If a question is off-topic, give a short redirect back to the persona."
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
        max_context_tokens: int | None = None,
    ) -> PromptBuildResult:
        """Return a compact prompt payload plus budgeting metadata."""
        persona = get_persona_profile()
        budget = PromptBudget.from_settings(max_context_tokens=max_context_tokens)
        compact_history = self._compact_history(history or [], budget)
        evidence_lines = self._format_evidence(validated_chunks, budget)

        system_parts = [system_instruction]
        if extra_rules:
            system_parts.extend(extra_rules)
        system_parts.append(f"Response style: {output_style}.")
        system_parts.append(_GROUNDING_RULE)
        system_parts.append(
            f"You represent {persona.name}. If the question is unsupported or off-topic, reply: "
            f"'{persona.refusal_message}'"
        )
        system_parts.append(
            f"If the user asks whether you are the real {persona.name} or a human, answer truthfully that "
            f"you are {persona.name}'s AI representative. Keep that reply brief and direct, and do not add a follow-up offer."
        )
        system_parts.append(_SCOPE_RULE)
        system_parts.append(_VOICE_RULE)
        system_parts.append(_BREVITY_RULE)
        system_parts.append(_LANGUAGE_RULE)
        system_message = "\n".join(system_parts)

        user_query = query.strip()
        user_message = self._build_user_message(user_query, evidence_lines)
        messages = self._assemble_messages(system_message, compact_history, user_message)
        estimated_tokens = estimate_message_tokens(messages)

        while estimated_tokens > budget.max_prompt_tokens and compact_history:
            compact_history = compact_history[1:]
            messages = self._assemble_messages(system_message, compact_history, user_message)
            estimated_tokens = estimate_message_tokens(messages)

        while estimated_tokens > budget.max_prompt_tokens and evidence_lines:
            evidence_lines = evidence_lines[:-1]
            user_message = self._build_user_message(user_query, evidence_lines)
            messages = self._assemble_messages(system_message, compact_history, user_message)
            estimated_tokens = estimate_message_tokens(messages)

        logger.debug(
            "Built prompt with %d system chars, %d user chars, %d history turns",
            len(system_message),
            len(user_message),
            len(compact_history),
        )

        return PromptBuildResult(
            messages=messages,
            metrics=PromptMetrics(
                estimated_prompt_tokens=estimated_tokens,
                prompt_token_limit=budget.max_prompt_tokens,
                history_messages_used=len(compact_history),
                history_messages_trimmed=max(0, len(history or []) - len(compact_history)),
                history_chars_used=sum(len(message["content"]) for message in compact_history),
                evidence_chunks_used=len(evidence_lines),
                evidence_chunks_trimmed=max(0, len(validated_chunks) - len(evidence_lines)),
                evidence_chars_used=sum(len(line) for line in evidence_lines),
                user_query_chars=len(user_query),
                within_budget=estimated_tokens <= budget.max_prompt_tokens,
            ),
        )

    @staticmethod
    def _assemble_messages(
        system_message: str,
        history: list[dict[str, str]],
        user_message: str,
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = [{"role": "system", "content": system_message}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})
        return messages

    @staticmethod
    def _compact_text(text: str, max_chars: int) -> str:
        cleaned = " ".join(text.split())
        if len(cleaned) <= max_chars:
            return cleaned
        return cleaned[: max_chars - 3].rstrip() + "..."

    def _compact_history(
        self,
        history: list[dict[str, str]],
        budget: PromptBudget,
    ) -> list[dict[str, str]]:
        if not history:
            return []

        recent = history[-budget.max_history_messages :]
        compacted: list[dict[str, str]] = []
        used_chars = 0

        for message in reversed(recent):
            content = self._compact_text(message.get("content", ""), 240)
            if not content:
                continue
            if used_chars + len(content) > budget.max_history_chars:
                if compacted:
                    break
                content = self._compact_text(content, budget.max_history_chars)
            compacted.append({"role": message.get("role", "user"), "content": content})
            used_chars += len(content)

        compacted.reverse()
        return compacted

    def _format_evidence(
        self,
        chunks: list[RerankResult],
        budget: PromptBudget,
    ) -> list[str]:
        if not chunks:
            return []

        lines: list[str] = []
        used_chars = 0
        for result in chunks[: budget.max_evidence_chunks]:
            line = f"[{len(lines) + 1}] {self._compact_text(result.chunk.text, budget.max_evidence_chunk_chars)}"
            if used_chars + len(line) > budget.max_evidence_chars:
                if lines:
                    break
                line = self._compact_text(line, budget.max_evidence_chars)
            lines.append(line)
            used_chars += len(line)
        return lines

    @staticmethod
    def _build_user_message(query: str, evidence_lines: list[str]) -> str:
        if not evidence_lines:
            return query
        evidence = "\n".join(evidence_lines)
        return f"Supporting information:\n{evidence}\n\nUser question:\n{query}"
