"""Local query guardrails that avoid unnecessary paid LLM calls."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.persona import get_persona_profile


@dataclass(frozen=True, slots=True)
class QueryGuardResult:
    """Outcome of running local guardrails on a user query."""

    blocked: bool
    reason: str | None = None
    response: str | None = None


_BLOCK_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "instruction_override",
        re.compile(r"\b(ignore|disregard|forget)\b.{0,40}\binstructions?\b", re.I),
    ),
    (
        "prompt_exfiltration",
        re.compile(r"\b(reveal|show|print|dump)\b.{0,40}\b(system|developer)\s+prompt\b", re.I),
    ),
    (
        "prompt_exfiltration",
        re.compile(r"\b(system|developer)\s+message\b", re.I),
    ),
    (
        "guardrail_bypass",
        re.compile(r"\b(jailbreak|bypass\s+(the\s+)?guardrails?|disable\s+safety)\b", re.I),
    ),
)


def guard_query(query: str) -> QueryGuardResult:
    """Block obvious prompt-injection attempts before retrieval or LLM usage."""
    normalized = " ".join(query.split())
    if not normalized:
        return QueryGuardResult(blocked=True, reason="empty_query", response="Please send a message.")

    persona = get_persona_profile()
    for reason, pattern in _BLOCK_PATTERNS:
        if pattern.search(normalized):
            return QueryGuardResult(
                blocked=True,
                reason=reason,
                response=persona.refusal_message,
            )

    return QueryGuardResult(blocked=False)
