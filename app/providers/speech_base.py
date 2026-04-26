"""Abstract base classes for speech synthesis providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass(frozen=True)
class SpeechOptions:
    """Runtime options for a text-to-speech request."""

    response_format: str = "mp3"
    voice: str | None = None
    instructions: str | None = None
    speed: float | None = None


class BaseSpeechProvider(ABC):
    """Interface every speech synthesis provider must implement."""

    @abstractmethod
    async def synthesize_stream(self, text: str, options: SpeechOptions) -> AsyncIterator[bytes]:
        """Yield encoded audio bytes for *text*."""
        ...

