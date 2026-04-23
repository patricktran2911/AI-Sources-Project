"""Free local categorisation for knowledge ingestion."""

from __future__ import annotations


_CATEGORY_RULES: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "profile": (
        ("Backend", ("python", "fastapi", "api", "backend", "postgres", "aws", "cloud")),
        ("Mobile", ("ios", "swift", "swiftui", "react native", "android", "mobile")),
        ("AI", ("ai", "llm", "rag", "machine learning", "embedding", "retrieval")),
        ("Leadership", ("lead", "mentor", "manager", "team", "stakeholder")),
        ("Education", ("university", "college", "degree", "education", "graduated", "study")),
    ),
    "projects": (
        ("AI Project", ("ai", "llm", "rag", "chatbot", "assistant")),
        ("Mobile Project", ("ios", "android", "react native", "swift", "mobile", "app store")),
        ("Platform Project", ("platform", "dashboard", "system", "portal", "workflow")),
        ("Web Project", ("web", "frontend", "backend", "fastapi", "react", "next.js")),
    ),
    "portfolio": (
        ("Highlight", ("highlight", "achievement", "launched", "delivered", "featured")),
        ("Client Work", ("client", "agency", "contract", "business")),
        ("Product", ("product", "app", "platform", "tool")),
    ),
    "general": (
        ("Availability", ("available", "availability", "timezone", "location", "contact")),
        ("Experience", ("experience", "background", "career", "years")),
        ("Skills", ("skill", "stack", "technology", "tools")),
    ),
}

_DEFAULT_LABELS = {
    "general": "General",
    "profile": "Background",
    "projects": "Project",
    "portfolio": "Highlight",
}


def infer_category(text: str, context: str) -> str:
    """Return a deterministic category label without using an LLM."""
    normalized = text.lower()
    for label, keywords in _CATEGORY_RULES.get(context, ()):
        if any(keyword in normalized for keyword in keywords):
            return label
    return _DEFAULT_LABELS.get(context, "General")
