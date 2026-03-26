"""Anthropic provider implementation."""

from __future__ import annotations

import logging

import anthropic

from app.core.config import get_settings
from app.core.exceptions import ProviderError
from app.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseLLMProvider):
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise ProviderError("anthropic", "ANTHROPIC_API_KEY not set")
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = settings.anthropic_model

    async def generate(self, messages: list[dict[str, str]], **kwargs) -> str:
        settings = get_settings()
        # Anthropic expects system as a separate param
        system_msg = ""
        user_messages = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                user_messages.append(m)

        try:
            response = await self._client.messages.create(
                model=self._model,
                system=system_msg,
                messages=user_messages,
                max_tokens=kwargs.get("max_tokens", settings.max_output_tokens),
                temperature=kwargs.get("temperature", 0.7),
            )
            return response.content[0].text
        except Exception as exc:
            logger.exception("Anthropic generation error")
            raise ProviderError("anthropic", str(exc)) from exc
