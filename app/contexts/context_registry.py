"""Context layer — defines per-context behaviour (instructions, rules, style)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ContextConfig:
    """Immutable descriptor for a single AI context."""

    name: str
    system_instruction: str
    output_style: str = "concise and helpful"
    extra_rules: list[str] = field(default_factory=list)
    max_context_tokens: int | None = None  # override per context


# ── Built-in context definitions ──────────────────────────────────────

_BUILTIN_CONTEXTS: dict[str, ContextConfig] = {
    "general": ContextConfig(
        name="general",
        system_instruction=(
            "You are a helpful AI assistant. Use the supporting information provided "
            "to give an accurate answer. If the supporting data is limited, still do "
            "your best to answer helpfully based on what you know. "
            "Always try to give the user a useful response."
        ),
    ),
    "profile": ContextConfig(
        name="profile",
        system_instruction=(
            "You are a personal AI assistant for Patrick Tran (also known as Phúc, Nguyên, Nguyen, Bin, or Bin đầu bạc — all these names refer to the same person). "
            "Answer questions about their background, skills, experience, projects, and tools "
            "using the supporting information provided. "
            "Be direct, honest, and concise — 1 to 3 sentences when possible. "
            "If the supporting data does not fully cover the question, answer as best you can "
            "with what is available, and mention if some details are beyond what you have."
        ),
        output_style="professional and concise",
        extra_rules=[
            "Never fabricate skills, projects, or experience not mentioned in the data.",
            "Keep answers under 80 words unless detail is explicitly requested.",
            "Do not use filler phrases like 'Certainly!' or 'Great question!'.",
        ],
    ),
    "projects": ContextConfig(
        name="projects",
        system_instruction=(
            "You are a project information assistant. Describe the user's projects, "
            "technologies, and contributions based on the supporting data. "
            "If the data is limited, still provide the best answer you can."
        ),
        output_style="technical and concise",
    ),
    "portfolio": ContextConfig(
        name="portfolio",
        system_instruction=(
            "You are a portfolio assistant. Highlight achievements, showcase work, "
            "and present the user's portfolio items attractively based on the supporting data. "
            "If the data is limited, still provide a helpful answer."
        ),
        output_style="engaging and professional",
    ),
}


class ContextRegistry:
    """Registry for looking up context configurations."""

    def __init__(self) -> None:
        self._contexts: dict[str, ContextConfig] = dict(_BUILTIN_CONTEXTS)

    def get(self, name: str) -> ContextConfig | None:
        return self._contexts.get(name)

    def register(self, config: ContextConfig) -> None:
        self._contexts[config.name] = config
        logger.info("Registered context: %s", config.name)

    def list_names(self) -> list[str]:
        return sorted(self._contexts.keys())
