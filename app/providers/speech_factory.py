"""Factory that returns the configured speech synthesis provider."""

from __future__ import annotations

from app.core.config import get_settings
from app.core.exceptions import SpeechProviderError
from app.providers.speech_base import BaseSpeechProvider


def get_speech_provider(name: str | None = None) -> BaseSpeechProvider:
    """Instantiate and return the requested speech provider."""
    name = (name or get_settings().speech_provider).lower()

    if name == "openai":
        from app.providers.openai_speech_provider import OpenAISpeechProvider

        return OpenAISpeechProvider()
    if name == "elevenlabs":
        from app.providers.elevenlabs_speech_provider import ElevenLabsSpeechProvider

        return ElevenLabsSpeechProvider()
    if name == "local":
        from app.providers.local_speech_provider import LocalSpeechProvider

        return LocalSpeechProvider()

    raise SpeechProviderError(name, "Unknown speech provider")
