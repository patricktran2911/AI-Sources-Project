"""Unit tests for internal layers (retrieval, validation, prompt builder, session store)."""

from __future__ import annotations

import asyncio
import json
import pickle
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from app.core.schemas import KnowledgeChunk, RetrievalResult, RerankResult
from app.features.session_store import SessionStore
from app.prompt.prompt_builder import PromptBuilder
from app.repository.knowledge_repo import KnowledgeRepository


# ── SessionStore ──────────────────────────────────────────────────────────────

class TestSessionStore:
    def test_new_session_returns_empty_history(self):
        store = SessionStore()
        assert store.get_history("new-id") == []

    def test_add_and_retrieve_turn(self):
        store = SessionStore()
        store.add_turn("s1", "Hello", "Hi there!")
        history = store.get_history("s1")
        assert history == [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

    def test_max_turns_enforced(self):
        store = SessionStore(max_turns=2)  # keeps 4 messages max
        for i in range(5):
            store.add_turn("s2", f"msg {i}", f"reply {i}")
        history = store.get_history("s2")
        assert len(history) == 4  # 2 turns × 2 messages

    def test_clear_removes_session(self):
        store = SessionStore()
        store.add_turn("s3", "hi", "hello")
        store.clear("s3")
        assert store.get_history("s3") == []

    def test_multiple_sessions_isolated(self):
        store = SessionStore()
        store.add_turn("alpha", "msg alpha", "reply alpha")
        store.add_turn("beta", "msg beta", "reply beta")
        assert len(store.get_history("alpha")) == 2
        assert len(store.get_history("beta")) == 2
        assert store.get_history("alpha")[0]["content"] == "msg alpha"


# ── PromptBuilder ─────────────────────────────────────────────────────────────

class TestPromptBuilder:
    def _make_chunk(self, text: str) -> RerankResult:
        return RerankResult(
            chunk=KnowledgeChunk(id="c1", text=text, category="profile"),
            score=1.0,
        )

    def test_build_returns_messages_list(self):
        builder = PromptBuilder()
        msgs = builder.build(
            query="What are Patrick's skills?",
            validated_chunks=[self._make_chunk("Patrick knows Python and FastAPI.")],
            system_instruction="You are a helpful assistant.",
        )
        assert isinstance(msgs, list)
        assert msgs[0]["role"] == "system"
        assert msgs[-1]["role"] == "user"

    def test_system_message_contains_instruction(self):
        builder = PromptBuilder()
        msgs = builder.build(
            query="q",
            validated_chunks=[self._make_chunk("some data")],
            system_instruction="Custom instruction here.",
        )
        assert "Custom instruction here." in msgs[0]["content"]

    def test_user_message_contains_query(self):
        builder = PromptBuilder()
        msgs = builder.build(
            query="Tell me about Patrick.",
            validated_chunks=[self._make_chunk("Patrick is an engineer.")],
            system_instruction="inst",
        )
        assert "Tell me about Patrick." in msgs[-1]["content"]

    def test_evidence_numbered_in_user_message(self):
        builder = PromptBuilder()
        chunks = [
            self._make_chunk("Chunk A content."),
            self._make_chunk("Chunk B content."),
        ]
        msgs = builder.build(query="q", validated_chunks=chunks, system_instruction="inst")
        user_content = msgs[-1]["content"]
        assert "[1]" in user_content
        assert "[2]" in user_content

    def test_history_injected_between_system_and_user(self):
        builder = PromptBuilder()
        history = [
            {"role": "user", "content": "first question"},
            {"role": "assistant", "content": "first answer"},
        ]
        msgs = builder.build(
            query="second question",
            validated_chunks=[self._make_chunk("data")],
            system_instruction="inst",
            history=history,
        )
        roles = [m["role"] for m in msgs]
        assert roles == ["system", "user", "assistant", "user"]

    def test_empty_chunks_yields_no_evidence_in_user_message(self):
        builder = PromptBuilder()
        msgs = builder.build(
            query="bare question",
            validated_chunks=[],
            system_instruction="inst",
        )
        user_content = msgs[-1]["content"]
        assert "Supporting information" not in user_content
        assert user_content == "bare question"

    def test_extra_rules_appended_to_system(self):
        builder = PromptBuilder()
        msgs = builder.build(
            query="q",
            validated_chunks=[self._make_chunk("data")],
            system_instruction="base",
            extra_rules=["Rule one.", "Rule two."],
        )
        system_content = msgs[0]["content"]
        assert "Rule one." in system_content
        assert "Rule two." in system_content


# ── KnowledgeRepository ───────────────────────────────────────────────────────

class TestKnowledgeRepository:
    """Tests for KnowledgeRepository using an asyncpg pool mock."""

    def _make_pool(self, rows: list[dict]) -> MagicMock:
        """Build a fake asyncpg pool that returns *rows* from fetch()."""
        pool = MagicMock()
        conn = MagicMock()

        async def async_fetch(*args, **kwargs):
            return rows

        async def async_execute(*args, **kwargs):
            pass

        conn.fetch = async_fetch
        conn.execute = async_execute

        class _AcquireCtx:
            async def __aenter__(self_):
                return conn

            async def __aexit__(self_, *a):
                pass

        pool.acquire = lambda: _AcquireCtx()
        return pool

    def _make_rows(self, context: str, n: int) -> list[dict]:
        return [
            {
                "id": f"{context}_{i}",
                "text": f"text {i}",
                "category": context,
                "metadata": "{}",
            }
            for i in range(n)
        ]

    @pytest.mark.asyncio
    async def test_load_profile_chunks(self):
        rows = self._make_rows("profile", 3)
        repo = KnowledgeRepository(pool=self._make_pool(rows))
        chunks = await repo.get_chunks("profile")
        assert len(chunks) == 3
        for chunk in chunks:
            assert chunk.text
            assert chunk.category == "profile"

    @pytest.mark.asyncio
    async def test_unknown_context_returns_empty_list(self):
        repo = KnowledgeRepository(pool=self._make_pool([]))
        chunks = await repo.get_chunks("does_not_exist")
        assert chunks == []

    @pytest.mark.asyncio
    async def test_get_chunks_with_user_id(self):
        rows = self._make_rows("chatbot", 2)
        repo = KnowledgeRepository(pool=self._make_pool(rows))
        chunks = await repo.get_chunks("chatbot", user_id="alice")
        assert len(chunks) == 2

    @pytest.mark.asyncio
    async def test_reload_is_noop(self):
        repo = KnowledgeRepository(pool=self._make_pool([]))
        # Should not raise
        await repo.reload()
        await repo.reload("profile")
