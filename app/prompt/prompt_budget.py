"""Prompt budgeting helpers for keeping request costs predictable."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil

from app.core.config import Settings, get_settings

_CHARS_PER_TOKEN_ESTIMATE = 4


def estimate_message_tokens(messages: list[dict[str, str]]) -> int:
    """Estimate prompt tokens from an OpenAI-style messages payload."""
    total_chars = sum(len(message["role"]) + len(message["content"]) for message in messages)
    return max(1, ceil(total_chars / _CHARS_PER_TOKEN_ESTIMATE))


@dataclass(frozen=True, slots=True)
class PromptBudget:
    """Character and token ceilings used to compact a prompt."""

    max_prompt_tokens: int
    max_history_messages: int
    max_history_chars: int
    max_evidence_chunks: int
    max_evidence_chars: int
    max_evidence_chunk_chars: int
    max_user_query_chars: int

    @classmethod
    def from_settings(
        cls,
        settings: Settings | None = None,
        *,
        max_context_tokens: int | None = None,
    ) -> PromptBudget:
        settings = settings or get_settings()
        return cls(
            max_prompt_tokens=max_context_tokens or settings.max_context_tokens,
            max_history_messages=settings.max_history_messages,
            max_history_chars=settings.max_history_chars,
            max_evidence_chunks=settings.max_evidence_chunks,
            max_evidence_chars=settings.max_evidence_chars,
            max_evidence_chunk_chars=settings.max_evidence_chunk_chars,
            max_user_query_chars=settings.max_user_query_chars,
        )


@dataclass(frozen=True, slots=True)
class PromptMetrics:
    """Prompt compaction and budgeting metadata."""

    estimated_prompt_tokens: int
    prompt_token_limit: int
    history_messages_used: int
    history_messages_trimmed: int
    history_chars_used: int
    evidence_chunks_used: int
    evidence_chunks_trimmed: int
    evidence_chars_used: int
    user_query_chars: int
    within_budget: bool

    def as_meta(self) -> dict[str, int | bool]:
        return {
            "estimated_prompt_tokens": self.estimated_prompt_tokens,
            "prompt_token_limit": self.prompt_token_limit,
            "history_messages_used": self.history_messages_used,
            "history_messages_trimmed": self.history_messages_trimmed,
            "history_chars_used": self.history_chars_used,
            "evidence_chunks_used": self.evidence_chunks_used,
            "evidence_chunks_trimmed": self.evidence_chunks_trimmed,
            "evidence_chars_used": self.evidence_chars_used,
            "user_query_chars": self.user_query_chars,
            "within_budget": self.within_budget,
        }


@dataclass(frozen=True, slots=True)
class PromptBuildResult:
    """Prompt payload plus budgeting metadata."""

    messages: list[dict[str, str]]
    metrics: PromptMetrics
