"""Abstract base classes for speech-to-text providers."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseTranscriptionProvider(ABC):
    """Interface every speech-to-text provider must implement."""

    @abstractmethod
    async def transcribe(
        self,
        audio: bytes,
        filename: str,
        content_type: str | None = None,
    ) -> str:
        """Return transcribed text for uploaded audio bytes."""
        ...
