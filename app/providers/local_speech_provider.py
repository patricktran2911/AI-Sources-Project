"""Local self-hosted speech provider implementation."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

import httpx

from app.core.config import get_settings
from app.core.exceptions import SpeechProviderError
from app.providers.speech_base import BaseSpeechProvider, SpeechOptions

logger = logging.getLogger(__name__)


class LocalSpeechProvider(BaseSpeechProvider):
    """Call a local voice-cloning service that returns encoded audio bytes."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.local_tts_url:
            raise SpeechProviderError("local", "LOCAL_TTS_URL not set")

        self._url = settings.local_tts_url
        self._api_key = settings.local_tts_api_key
        self._reference_audio_path = settings.local_tts_reference_audio_path
        self._reference_text = settings.local_tts_reference_text
        self._model = settings.local_tts_model
        self._timeout = settings.local_tts_timeout_seconds
        self._chunk_size = settings.speech_chunk_size

    async def synthesize_stream(self, text: str, options: SpeechOptions) -> AsyncIterator[bytes]:
        payload: dict[str, object] = {
            "text": text,
            "response_format": options.response_format,
            "reference_audio_path": self._reference_audio_path,
            "reference_text": self._reference_text,
            "model": self._model,
        }
        if options.voice:
            payload["voice"] = options.voice
        if options.instructions:
            payload["instructions"] = options.instructions
        if options.speed is not None:
            payload["speed"] = options.speed

        headers = {"Accept": "application/octet-stream"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream("POST", self._url, headers=headers, json=payload) as response:
                    if response.status_code >= 400:
                        error_text = await response.aread()
                        raise SpeechProviderError(
                            "local",
                            error_text.decode("utf-8", errors="replace")[:800],
                        )
                    async for chunk in response.aiter_bytes(self._chunk_size):
                        if chunk:
                            yield chunk
        except SpeechProviderError:
            raise
        except Exception as exc:
            logger.exception("Local speech synthesis error")
            raise SpeechProviderError("local", str(exc)) from exc

