"""Factory that returns the configured speech-to-text provider."""

from __future__ import annotations

from app.core.config import get_settings
from app.core.exceptions import TranscriptionProviderError
from app.providers.transcription_base import BaseTranscriptionProvider


def get_transcription_provider(name: str | None = None) -> BaseTranscriptionProvider:
    """Instantiate and return the requested transcription provider."""
    name = (name or get_settings().transcription_provider).lower()

    if name == "openai":
        from app.providers.openai_transcription_provider import OpenAITranscriptionProvider

        return OpenAITranscriptionProvider()

    raise TranscriptionProviderError(name, "Unknown transcription provider")
