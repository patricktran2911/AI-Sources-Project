"""OpenAI text-to-speech provider implementation."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.core.exceptions import SpeechProviderError
from app.providers.speech_base import BaseSpeechProvider, SpeechOptions

logger = logging.getLogger(__name__)


class OpenAISpeechProvider(BaseSpeechProvider):
    """Generate speech audio through the OpenAI Audio API."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise SpeechProviderError("openai", "OPENAI_API_KEY not set")
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_tts_model
        self._voice = settings.openai_tts_voice
        self._voice_id = settings.openai_tts_voice_id
        self._instructions = settings.openai_tts_instructions
        self._response_format = settings.openai_tts_response_format
        self._chunk_size = settings.speech_chunk_size

    def _resolve_voice(self, override: str | None) -> str | dict[str, str]:
        selected = (override or self._voice_id or self._voice).strip()
        if selected.startswith("voice_") or (not override and self._voice_id):
            return {"id": selected}
        return selected

    async def synthesize_stream(self, text: str, options: SpeechOptions) -> AsyncIterator[bytes]:
        response_format = options.response_format or self._response_format
        instructions = options.instructions if options.instructions is not None else self._instructions

        payload = {
            "model": self._model,
            "voice": self._resolve_voice(options.voice),
            "input": text,
            "response_format": response_format,
            "stream_format": "audio",
        }
        if instructions:
            payload["instructions"] = instructions
        if options.speed is not None:
            payload["speed"] = options.speed

        try:
            async with self._client.audio.speech.with_streaming_response.create(**payload) as response:
                async for chunk in response.iter_bytes(self._chunk_size):
                    if chunk:
                        yield chunk
        except Exception as exc:
            logger.exception("OpenAI speech synthesis error")
            raise SpeechProviderError("openai", str(exc)) from exc

