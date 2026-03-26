"""OpenAI provider implementation."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.core.exceptions import ProviderError
from app.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise ProviderError("openai", "OPENAI_API_KEY not set")
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model

    async def generate(self, messages: list[dict[str, str]], **kwargs) -> str:
        settings = get_settings()
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=kwargs.get("max_tokens", settings.max_output_tokens),
                temperature=kwargs.get("temperature", 0.7),
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.exception("OpenAI generation error")
            raise ProviderError("openai", str(exc)) from exc

    async def stream_generate(self, messages: list[dict[str, str]], **kwargs) -> AsyncIterator[str]:
        settings = get_settings()
        try:
            stream = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=kwargs.get("max_tokens", settings.max_output_tokens),
                temperature=kwargs.get("temperature", 0.7),
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield delta.content
        except Exception as exc:
            logger.exception("OpenAI streaming error")
            raise ProviderError("openai", str(exc)) from exc
