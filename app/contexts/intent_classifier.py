"""Lightweight intent classifier — no LLM call, keyword + pattern based."""

from __future__ import annotations

import logging
import re
from enum import Enum

logger = logging.getLogger(__name__)


class Intent(str, Enum):
    FACTUAL = "factual"
    COMPARISON = "comparison"
    CREATIVE = "creative"
    LIST = "list"
    OPINION = "opinion"
    GREETING = "greeting"


# Patterns checked in order; first match wins.
_PATTERNS: list[tuple[Intent, re.Pattern[str]]] = [
    (Intent.GREETING, re.compile(
        r"^(hi|hello|hey|good\s*(morning|afternoon|evening)|what'?s\s*up)\b", re.I)),
    (Intent.LIST, re.compile(
        r"\b(list|enumerate|name\s+all|give\s+me\s+(all|a\s+list)|how\s+many)\b", re.I)),
    (Intent.COMPARISON, re.compile(
        r"\b(compare|versus|vs\.?|difference\s+between|better\s+than|which\s+is\s+better)\b", re.I)),
    (Intent.CREATIVE, re.compile(
        r"\b(write|draft|compose|create|generate|suggest\s+(a\s+)?name|brainstorm)\b", re.I)),
    (Intent.OPINION, re.compile(
        r"\b(do\s+you\s+think|your\s+opinion|what\s+do\s+you\s+recommend|should\s+i)\b", re.I)),
]


def classify_intent(query: str) -> Intent:
    """Classify the user query into an intent using keyword patterns.

    Falls back to ``Intent.FACTUAL`` when no specific pattern matches.
    """
    for intent, pattern in _PATTERNS:
        if pattern.search(query):
            logger.debug("Intent classified as %s for query: %s", intent.value, query[:80])
            return intent
    return Intent.FACTUAL


# Extra prompt hints the PromptBuilder can append depending on intent.
INTENT_PROMPT_HINTS: dict[Intent, str] = {
    Intent.FACTUAL: "Answer directly and factually based on the evidence.",
    Intent.COMPARISON: "Structure your answer as a clear comparison, highlighting key differences and similarities.",
    Intent.LIST: "Present the answer as a well-organised numbered or bulleted list.",
    Intent.CREATIVE: "Be creative while staying grounded in the available information.",
    Intent.OPINION: "Provide a balanced perspective grounded in the available evidence.",
    Intent.GREETING: "Respond warmly and briefly, then offer to help.",
}
