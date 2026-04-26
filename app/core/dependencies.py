"""Centralised FastAPI dependency functions.

All route handlers should retrieve application components through these
dependencies rather than accessing ``request.app.state`` directly.  This
keeps routing code decoupled from the application startup lifecycle and
makes handler signatures self-documenting.

Usage::

    from typing import Annotated
    from fastapi import Depends
    from app.core.dependencies import OrchestratorDep, KnowledgeRepoDep

    @router.post("/chat")
    async def chat(body: ChatRequest, orchestrator: OrchestratorDep): ...
"""

from __future__ import annotations

from typing import Annotated

import asyncpg
from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.orchestration.orchestrator import Orchestrator
from app.repository.knowledge_repo import KnowledgeRepository
from app.providers.base import BaseLLMProvider
from app.providers.speech_base import BaseSpeechProvider
from app.providers.transcription_base import BaseTranscriptionProvider
from app.features.session_store import SessionStore
from app.features.registry import FeatureRegistry
from app.contexts.context_registry import ContextRegistry
from app.core.rate_limiter import RateLimiter


# ── primitive settings dependency ─────────────────────────────────────

def get_config() -> Settings:
    """Return the application settings singleton."""
    return get_settings()


# ── app-state accessor functions used by Depends() ────────────────────

def _get_orchestrator(request: Request) -> Orchestrator:
    return request.app.state.orchestrator


def _get_knowledge_repo(request: Request) -> KnowledgeRepository:
    return request.app.state.knowledge_repo


def _get_provider(request: Request) -> BaseLLMProvider:
    return request.app.state.provider


def _get_speech_provider(request: Request) -> BaseSpeechProvider:
    provider = getattr(request.app.state, "speech_provider", None)
    if provider is None:
        from app.providers.speech_factory import get_speech_provider

        provider = get_speech_provider()
        request.app.state.speech_provider = provider
    return provider


def _get_transcription_provider(request: Request) -> BaseTranscriptionProvider:
    provider = getattr(request.app.state, "transcription_provider", None)
    if provider is None:
        from app.providers.transcription_factory import get_transcription_provider

        provider = get_transcription_provider()
        request.app.state.transcription_provider = provider
    return provider


def _get_session_store(request: Request) -> SessionStore:
    return request.app.state.session_store


def _get_feature_registry(request: Request) -> FeatureRegistry:
    return request.app.state.feature_registry


def _get_context_registry(request: Request) -> ContextRegistry:
    return request.app.state.context_registry


def _get_rate_limiter(request: Request) -> RateLimiter:
    return request.app.state.rate_limiter


def _get_db_pool(request: Request):
    """Return the asyncpg connection pool from app state."""
    return request.app.state.pool


# ── typed aliases — import these in route handlers ─────────────────────
#
#   Each alias combines the concrete type with the Depends() call so that:
#   1. The IDE provides full type checking and autocompletion.
#   2. FastAPI resolves the dependency automatically.
#   3. Tests can override them with ``app.dependency_overrides``.

SettingsDep       = Annotated[Settings,         Depends(get_config)]
OrchestratorDep   = Annotated[Orchestrator,     Depends(_get_orchestrator)]
KnowledgeRepoDep  = Annotated[KnowledgeRepository, Depends(_get_knowledge_repo)]
ProviderDep       = Annotated[BaseLLMProvider,  Depends(_get_provider)]
SpeechProviderDep = Annotated[BaseSpeechProvider, Depends(_get_speech_provider)]
TranscriptionProviderDep = Annotated[BaseTranscriptionProvider, Depends(_get_transcription_provider)]
SessionStoreDep   = Annotated[SessionStore,     Depends(_get_session_store)]
FeatureRegistryDep = Annotated[FeatureRegistry, Depends(_get_feature_registry)]
ContextRegistryDep = Annotated[ContextRegistry, Depends(_get_context_registry)]
DbPoolDep          = Annotated[asyncpg.Pool,    Depends(_get_db_pool)]

