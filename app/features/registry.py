"""Feature registry - maps feature names to their service classes."""

from __future__ import annotations

from app.features.base import BaseFeature
from app.features.chatbot.feature import ChatFeature
from app.prompt.prompt_builder import PromptBuilder
from app.providers.base import BaseLLMProvider


class FeatureRegistry:
    """Instantiate and look up feature services by name."""

    def __init__(self, provider: BaseLLMProvider, prompt_builder: PromptBuilder) -> None:
        self._features: dict[str, BaseFeature] = {}
        self._provider = provider
        self._prompt_builder = prompt_builder
        self._register_defaults()

    def get(self, name: str) -> BaseFeature | None:
        return self._features.get(name)

    def register(self, feature: BaseFeature) -> None:
        self._features[feature.name] = feature

    def list_names(self) -> list[str]:
        return sorted(self._features.keys())

    def _register_defaults(self) -> None:
        self.register(ChatFeature(provider=self._provider, prompt_builder=self._prompt_builder))
