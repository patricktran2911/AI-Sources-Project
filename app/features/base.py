"""Base class and registry for AI feature services."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from app.core.schemas import AIRequest


class BaseFeature(ABC):
    """Every AI feature must implement this interface."""

    name: str = ""

    @abstractmethod
    async def execute(self, request: AIRequest, context_data: list[Any], **kwargs) -> dict[str, Any]:
        """Run the feature logic and return the data dict for AIResponse."""
        ...

    async def stream_execute(
        self, request: AIRequest, context_data: list[Any], **kwargs
    ) -> AsyncIterator[str]:
        """Yield text chunks for streaming responses.

        Default falls back to execute() and yields the full result at once.
        """
        data = await self.execute(request, context_data, **kwargs)
        yield data.get("answer", data.get("result", ""))
