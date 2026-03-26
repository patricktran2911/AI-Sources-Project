"""Factory that returns the configured LLM provider."""

from __future__ import annotations

from app.core.config import get_settings
from app.core.exceptions import ProviderError
from app.providers.base import BaseLLMProvider


def get_provider(name: str | None = None) -> BaseLLMProvider:
    """Instantiate and return the requested (or configured) LLM provider."""
    name = (name or get_settings().llm_provider).lower()

    if name == "openai":
        from app.providers.openai_provider import OpenAIProvider
        return OpenAIProvider()
    if name == "anthropic":
        from app.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider()
    if name == "gemini":
        from app.providers.gemini_provider import GeminiProvider
        return GeminiProvider()

    raise ProviderError(name, "Unknown provider")
