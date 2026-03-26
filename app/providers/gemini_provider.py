"""Google Gemini provider implementation."""

from __future__ import annotations

import logging

from google import genai

from app.core.config import get_settings
from app.core.exceptions import ProviderError
from app.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class GeminiProvider(BaseLLMProvider):
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise ProviderError("gemini", "GEMINI_API_KEY not set")
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_model

    async def generate(self, messages: list[dict[str, str]], **kwargs) -> str:
        settings = get_settings()
        # Convert to Gemini format: system instruction + contents
        system_instruction = ""
        contents: list[str] = []
        for m in messages:
            if m["role"] == "system":
                system_instruction = m["content"]
            else:
                contents.append(m["content"])

        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents="\n".join(contents),
                config=genai.types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    max_output_tokens=kwargs.get("max_tokens", settings.max_output_tokens),
                    temperature=kwargs.get("temperature", 0.7),
                ),
            )
            return response.text or ""
        except Exception as exc:
            logger.exception("Gemini generation error")
            raise ProviderError("gemini", str(exc)) from exc
