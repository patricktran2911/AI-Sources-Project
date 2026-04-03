"""Shared pytest fixtures for all tests."""

from __future__ import annotations

import asyncio
import json
import sys
import types
from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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
# Stub asyncpg — no real Postgres required for tests
# ---------------------------------------------------------------------------

# In-memory store shared across all FakePool instances in a test session.
_DB_STORE: list[dict] = []
_DB_PK = [0]


def _install_asyncpg_stub():
    asyncpg_mod = types.ModuleType("asyncpg")

    class _FakeConn:
        """In-memory asyncpg connection that actually stores / retrieves rows."""

        # ── helpers ──────────────────────────────────────────────────
        @staticmethod
        def _q(sql: str) -> str:
            """Normalise SQL for pattern matching."""
            return " ".join(sql.split()).upper()

        # ── fetch (SELECT) ────────────────────────────────────────────
        async def fetch(self, query, *args, **kw):
            q = self._q(query)

            # Seed count / GROUP BY — return empty (no seeded data in tests)
            if "COUNT(*)" in q or "GROUP BY" in q:
                return []

            # SELECT DISTINCT context WHERE user_id IS NULL
            if "SELECT DISTINCT CONTEXT" in q:
                contexts = sorted({r["context"] for r in _DB_STORE if r["user_id"] is None})
                return [{"context": c} for c in contexts]

            # get_chunks merged: context=$1 AND (user_id IS NULL OR user_id=$2)
            if "USER_ID IS NULL OR USER_ID = $2" in q:
                ctx, uid = args[0], args[1]
                return [dict(r) for r in _DB_STORE
                        if r["context"] == ctx and (r["user_id"] is None or r["user_id"] == uid)]

            # get_all_user_chunks / _list_with_context: WHERE user_id=$1
            if "WHERE USER_ID = $1" in q:
                uid = args[0]
                rows = [dict(r) for r in _DB_STORE if r["user_id"] == uid]
                if "AND CONTEXT = $2" in q and len(args) > 1:
                    rows = [r for r in rows if r["context"] == args[1]]
                return rows

            # get_chunks_global: WHERE context=$1 AND user_id IS NULL
            if "WHERE CONTEXT = $1" in q and "USER_ID IS NULL" in q:
                ctx = args[0]
                return [dict(r) for r in _DB_STORE
                        if r["context"] == ctx and r["user_id"] is None]

            return []

        # ── execute (INSERT / DELETE) ─────────────────────────────────
        async def execute(self, query, *args, **kw):
            q = self._q(query)
            if "INSERT INTO KNOWLEDGE_CHUNKS" in q:
                _DB_PK[0] += 1
                _DB_STORE.append({
                    "pk": _DB_PK[0],
                    "id": args[0],
                    "context": args[1],
                    "text": args[2],
                    "category": args[3],
                    "metadata": args[4],
                    "user_id": args[5] if len(args) > 5 else None,
                })
            elif "DELETE FROM KNOWLEDGE_CHUNKS" in q and "RETURNING" not in q:
                ctx, uid = args[0], args[1]
                _DB_STORE[:] = [r for r in _DB_STORE
                                if not (r["context"] == ctx and r["user_id"] == uid)]

        async def executemany(self, query, rows, **kw):
            for row in rows:
                await self.execute(query, *row)

        # ── fetchrow (DELETE...RETURNING) ─────────────────────────────
        async def fetchrow(self, query, *args, **kw):
            q = self._q(query)
            if "DELETE FROM KNOWLEDGE_CHUNKS" in q and "RETURNING" in q:
                chunk_id, uid = args[0], args[1]
                for i, r in enumerate(_DB_STORE):
                    if r["id"] == chunk_id and r["user_id"] == uid:
                        _DB_STORE.pop(i)
                        return {"id": chunk_id}
                return None
            return None

        # ── fetchval (SELECT 1 probe) ─────────────────────────────────
        async def fetchval(self, query, *args, **kw):
            return 1

    class FakePool:
        """asyncpg pool backed by the shared in-memory _DB_STORE."""

        class _Ctx:
            def __init__(self, conn):
                self._conn = conn
            async def __aenter__(self):
                return self._conn
            async def __aexit__(self, *a):
                pass

        def __init__(self):
            self._conn = _FakeConn()

        def acquire(self):
            return self._Ctx(self._conn)

        async def close(self):
            pass

    asyncpg_mod.Pool = FakePool
    asyncpg_mod.create_pool = AsyncMock(return_value=FakePool())
    sys.modules.setdefault("asyncpg", asyncpg_mod)


_install_asyncpg_stub()

# ---------------------------------------------------------------------------
# Stub the database migration layer so it never touches a real DB
# ---------------------------------------------------------------------------

def _stub_db_layer():
    db_mod = types.ModuleType("app.database")
    conn_mod = types.ModuleType("app.database.connection")
    mig_mod = types.ModuleType("app.database.migrations")

    async def _fake_create_pool(dsn: str):
        import asyncpg
        return asyncpg.create_pool.return_value

    async def _fake_run_migrations(pool):
        pass

    async def _fake_seed(pool, data_dir: Path):
        pass

    conn_mod.create_pool = _fake_create_pool
    mig_mod.run_migrations = _fake_run_migrations
    mig_mod.seed_from_json = _fake_seed

    sys.modules.setdefault("app.database", db_mod)
    sys.modules.setdefault("app.database.connection", conn_mod)
    sys.modules.setdefault("app.database.migrations", mig_mod)


_stub_db_layer()

# ---------------------------------------------------------------------------
# Fake LLM provider — no API key required, returns deterministic answers
# ---------------------------------------------------------------------------

class FakeLLMProvider:
    async def generate(self, messages, **kwargs) -> str:
        # Short label when called from knowledge add (max_tokens=20)
        if kwargs.get("max_tokens", 512) <= 20:
            return "Test Category Label"
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
