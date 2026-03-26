"""Shared pytest fixtures for all tests."""

from __future__ import annotations

import sys
import types
from collections.abc import AsyncIterator
from unittest.mock import patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

# ---------------------------------------------------------------------------
# Stub sentence_transformers before any app module imports it.
# sentence-transformers is heavy; the conda base env may not have it.
# ---------------------------------------------------------------------------

def _install_st_stubs():
    import numpy as np

    class _FakeST:
        def __init__(self, *a, **kw): pass
        def encode(self, texts, **kw):
            n = len(texts) if isinstance(texts, list) else 1
            return np.ones((n, 384), dtype="float32")

    class _FakeCE:
        def __init__(self, *a, **kw): pass
        def predict(self, pairs):
            return np.array([1.0] * len(pairs))

    st = types.ModuleType("sentence_transformers")
    st.SentenceTransformer = _FakeST
    st.CrossEncoder = _FakeCE
    ce = types.ModuleType("sentence_transformers.cross_encoder")
    ce.CrossEncoder = _FakeCE
    st.cross_encoder = ce

    sys.modules.setdefault("sentence_transformers", st)
    sys.modules.setdefault("sentence_transformers.cross_encoder", ce)


_install_st_stubs()

# ---------------------------------------------------------------------------
# Fake LLM provider — no API key required, returns deterministic answers
# ---------------------------------------------------------------------------

class FakeLLMProvider:
    async def generate(self, messages, **kwargs) -> str:
        return "Patrick is a full-stack engineer with skills in Python, FastAPI, and iOS development."

    async def stream_generate(self, messages, **kwargs) -> AsyncIterator[str]:
        for token in ("Patrick ", "is ", "a ", "full-stack ", "engineer."):
            yield token


# ---------------------------------------------------------------------------
# App fixture — built once per test session
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    from main import create_app
    return create_app()


# ---------------------------------------------------------------------------
# Patch the provider factory so the lifespan never tries to connect to an LLM.
# The patch wraps the TestClient context so it is active during lifespan startup.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def client(app):
    """Synchronous TestClient with the real lifespan but a fake LLM provider."""
    fake = FakeLLMProvider()
    with patch("app.providers.factory.get_provider", return_value=fake):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


@pytest_asyncio.fixture(scope="function")
async def async_client(app):
    """Async httpx client for streaming tests."""
    fake = FakeLLMProvider()
    with patch("app.providers.factory.get_provider", return_value=fake):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac


