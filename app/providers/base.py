"""Abstract base for LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class BaseLLMProvider(ABC):
    """Interface every LLM provider must implement."""

    @abstractmethod
    async def generate(self, messages: list[dict[str, str]], **kwargs) -> str:
        """Send *messages* to the LLM and return the generated text."""
        ...

    async def stream_generate(self, messages: list[dict[str, str]], **kwargs) -> AsyncIterator[str]:
        """Yield text chunks as they arrive from the LLM.

        Default implementation falls back to a single-chunk generate() call.
        Providers that support native streaming should override this.
        """
        text = await self.generate(messages, **kwargs)
        yield text
