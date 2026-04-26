"""OpenAI speech-to-text provider implementation."""

from __future__ import annotations

import logging

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.core.exceptions import TranscriptionProviderError
from app.providers.transcription_base import BaseTranscriptionProvider

logger = logging.getLogger(__name__)


class OpenAITranscriptionProvider(BaseTranscriptionProvider):
    """Transcribe user speech through the OpenAI Audio API."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise TranscriptionProviderError("openai", "OPENAI_API_KEY not set")
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_stt_model
        self._prompt = settings.openai_stt_prompt

    async def transcribe(
        self,
        audio: bytes,
        filename: str,
        content_type: str | None = None,
    ) -> str:
        payload: dict[str, object] = {
            "model": self._model,
            "file": (
                filename or "speech.webm",
                audio,
                content_type or "application/octet-stream",
            ),
            "response_format": "text",
        }
        if self._prompt:
            payload["prompt"] = self._prompt

        try:
            transcript = await self._client.audio.transcriptions.create(**payload)
            return str(getattr(transcript, "text", transcript)).strip()
        except Exception as exc:
            logger.exception("OpenAI speech transcription error")
            raise TranscriptionProviderError("openai", str(exc)) from exc
