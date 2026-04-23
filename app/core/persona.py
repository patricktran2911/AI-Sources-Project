"""Persona configuration helpers used across prompts, routes, and docs."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from app.core.config import get_settings


def _possessive(name: str) -> str:
    stripped = name.strip()
    if not stripped:
        return "the persona's"
    return f"{stripped}'" if stripped.endswith(("s", "S")) else f"{stripped}'s"


@dataclass(frozen=True, slots=True)
class PersonaProfile:
    """Runtime persona metadata derived from settings."""

    name: str
    aliases: tuple[str, ...]
    possessive_name: str
    refusal_message: str
    scope_summary: str

    @property
    def alias_text(self) -> str:
        if not self.aliases:
            return ""
        return ", ".join(self.aliases)


@lru_cache()
def get_persona_profile() -> PersonaProfile:
    """Return the configured persona profile."""
    settings = get_settings()
    aliases = tuple(
        dict.fromkeys(
            alias.strip()
            for alias in settings.persona_aliases.split(",")
            if alias.strip()
        )
    )
    possessive_name = _possessive(settings.persona_name)
    refusal_message = (
        f"I'm {possessive_name} personal AI assistant and can only help with questions "
        f"about {settings.persona_name}. Try asking about {possessive_name} background, "
        "skills, projects, or experience."
    )
    scope_summary = (
        f"You represent {settings.persona_name} and must stay grounded in approved "
        f"knowledge about {settings.persona_name}."
    )
    return PersonaProfile(
        name=settings.persona_name,
        aliases=aliases,
        possessive_name=possessive_name,
        refusal_message=refusal_message,
        scope_summary=scope_summary,
    )
