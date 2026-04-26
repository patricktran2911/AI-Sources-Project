"""ElevenLabs text-to-speech provider implementation."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

import httpx

from app.core.config import get_settings
from app.core.exceptions import SpeechProviderError
from app.providers.speech_base import BaseSpeechProvider, SpeechOptions

logger = logging.getLogger(__name__)

ELEVENLABS_FORMATS = {
    "mp3": "mp3_44100_128",
    "wav": "wav_44100",
    "pcm": "pcm_24000",
}


class ElevenLabsSpeechProvider(BaseSpeechProvider):
    """Generate streaming speech audio through ElevenLabs."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.elevenlabs_api_key:
            raise SpeechProviderError("elevenlabs", "ELEVENLABS_API_KEY not set")
        if not settings.elevenlabs_voice_id:
            raise SpeechProviderError("elevenlabs", "ELEVENLABS_VOICE_ID not set")

        self._api_key = settings.elevenlabs_api_key
        self._voice_id = settings.elevenlabs_voice_id
        self._model = settings.elevenlabs_model
        self._output_format = settings.elevenlabs_output_format
        self._chunk_size = settings.speech_chunk_size
        self._voice_settings = {
            "stability": settings.elevenlabs_stability,
            "similarity_boost": settings.elevenlabs_similarity_boost,
            "style": settings.elevenlabs_style,
            "use_speaker_boost": settings.elevenlabs_use_speaker_boost,
        }

    def _resolve_output_format(self, requested_format: str) -> str:
        if requested_format == "mp3":
            return self._output_format
        if requested_format in ELEVENLABS_FORMATS:
            return ELEVENLABS_FORMATS[requested_format]
        raise SpeechProviderError(
            "elevenlabs",
            f"Response format '{requested_format}' is not supported by the ElevenLabs provider.",
        )

    async def synthesize_stream(self, text: str, options: SpeechOptions) -> AsyncIterator[bytes]:
        output_format = self._resolve_output_format(options.response_format)
        voice_id = options.voice or self._voice_id
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"

        payload: dict[str, object] = {
            "text": text,
            "model_id": self._model,
            "voice_settings": dict(self._voice_settings),
        }
        if options.speed is not None:
            payload["voice_settings"]["speed"] = options.speed

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    url,
                    headers={"xi-api-key": self._api_key, "Content-Type": "application/json"},
                    params={"output_format": output_format},
                    json=payload,
                ) as response:
                    if response.status_code >= 400:
                        error_text = await response.aread()
                        raise SpeechProviderError(
                            "elevenlabs",
                            error_text.decode("utf-8", errors="replace")[:800],
                        )
                    async for chunk in response.aiter_bytes(self._chunk_size):
                        if chunk:
                            yield chunk
        except SpeechProviderError:
            raise
        except Exception as exc:
            logger.exception("ElevenLabs speech synthesis error")
            raise SpeechProviderError("elevenlabs", str(exc)) from exc
