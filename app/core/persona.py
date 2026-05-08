"""Persona configuration helpers used across prompts, routes, and docs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from app.core.config import get_settings


def _possessive(name: str) -> str:
    stripped = name.strip()
    if not stripped:
        return "the persona's"
    return f"{stripped}'" if stripped.endswith(("s", "S")) else f"{stripped}'s"


_THIRD_PERSON_REQUEST_RE = re.compile(r"\b(third[-\s]?person|3rd[-\s]?person)\b", re.IGNORECASE)
_COMMON_THIRD_PERSON_VERBS = {
    "is": "am",
    "was": "was",
    "has": "have",
    "does": "do",
    "knows": "know",
    "builds": "build",
    "uses": "use",
    "works": "work",
    "creates": "create",
    "focuses": "focus",
    "connects": "connect",
    "designs": "design",
    "develops": "develop",
    "writes": "write",
    "brings": "bring",
    "combines": "combine",
    "prefers": "prefer",
    "cares": "care",
    "likes": "like",
    "wants": "want",
    "needs": "need",
    "leads": "lead",
    "owns": "own",
    "manages": "manage",
    "learns": "learn",
    "lives": "live",
}


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

    @property
    def first_name(self) -> str:
        return self.name.split()[0] if self.name.split() else self.name

    @property
    def response_names(self) -> tuple[str, ...]:
        names = [self.name, self.first_name, *self.aliases]
        return tuple(dict.fromkeys(name.strip() for name in names if name.strip()))


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
        "I can answer from my own context and the information I've shared, but I can't act as a general ChatGPT. "
        "Ask me about my life, school, work, projects, job search, location, or what I would think about something."
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


def should_answer_in_first_person(query: str) -> bool:
    """Return whether normal persona answers should use "I/me/my" wording."""
    return _THIRD_PERSON_REQUEST_RE.search(query or "") is None


def normalize_first_person_answer(answer: str, query: str) -> str:
    """Convert common third-person self references into first-person wording.

    This is intentionally conservative: it protects the default chat and voice
    experience from answers like "Patrick builds..." while preserving explicit
    third-person requests.
    """
    if not answer or not should_answer_in_first_person(query):
        return answer

    persona = get_persona_profile()
    normalized = answer
    names = sorted(persona.response_names, key=len, reverse=True)
    if not names:
        return normalized

    name_pattern = "|".join(re.escape(name) for name in names)

    normalized = re.sub(
        rf"\b(?:{name_pattern})(?:'|\u2019)s\b",
        "my",
        normalized,
        flags=re.IGNORECASE,
    )

    normalized = re.sub(
        rf"\b(?P<prep>about|for|to|with|from)\s+(?:{name_pattern})\b",
        lambda match: f"{match.group('prep')} me",
        normalized,
        flags=re.IGNORECASE,
    )

    def replace_named_verb(match: re.Match[str]) -> str:
        verb = match.group("verb").lower()
        replacement = _COMMON_THIRD_PERSON_VERBS.get(verb, verb)
        return f"I {replacement}"

    normalized = re.sub(
        rf"\b(?:{name_pattern})\s+(?P<verb>{'|'.join(_COMMON_THIRD_PERSON_VERBS)})\b",
        replace_named_verb,
        normalized,
        flags=re.IGNORECASE,
    )

    normalized = re.sub(r"\b[Ii]\s+am\b", "I'm", normalized)
    normalized = re.sub(r"\b[Ii]\s+have\b", "I have", normalized)
    normalized = re.sub(r"\b[Hh]is\b", "my", normalized)
    normalized = re.sub(r"\b[Hh]im\b", "me", normalized)

    def replace_he_verb(match: re.Match[str]) -> str:
        verb = match.group("verb").lower()
        replacement = _COMMON_THIRD_PERSON_VERBS.get(verb, verb)
        return f"I {replacement}"

    normalized = re.sub(
        rf"\b[Hh]e\s+(?P<verb>{'|'.join(_COMMON_THIRD_PERSON_VERBS)})\b",
        replace_he_verb,
        normalized,
        flags=re.IGNORECASE,
    )

    # Preserve identity phrases like "I'm Phuc Tran, also known as Patrick Tran".
    # Replacing every standalone name corrupts real names into artifacts such as "I Tran".
    normalized = re.sub(r"(?<=[.!?])(?=(?:I'm|I\s|[A-Z][a-z]))", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized
