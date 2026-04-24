"""Unit tests for prompt budgeting, session state, and repository helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.contexts.context_registry import ContextRegistry
from app.contexts.context_router import ContextRouter, _KEYWORD_HINTS, _forced_context
from app.contexts.knowledge_categorizer import infer_category
from app.core.schemas import KnowledgeChunk, RerankResult, RetrievalResult
from app.features.session_store import SessionStore
from app.prompt.prompt_builder import PromptBuilder
from app.repository.knowledge_repo import KnowledgeRepository


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
        store = SessionStore(max_turns=2)
        for i in range(5):
            store.add_turn("s2", f"msg {i}", f"reply {i}")
        history = store.get_history("s2")
        assert len(history) == 4

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


class TestPromptBuilder:
    def _make_chunk(self, text: str) -> RerankResult:
        return RerankResult(
            chunk=KnowledgeChunk(id="c1", text=text, category="profile"),
            score=1.0,
        )

    def test_build_returns_messages_list(self):
        builder = PromptBuilder()
        result = builder.build(
            query="What are Patrick's skills?",
            validated_chunks=[self._make_chunk("Patrick knows Python and FastAPI.")],
            system_instruction="You are a helpful assistant.",
        )
        assert isinstance(result.messages, list)
        assert result.messages[0]["role"] == "system"
        assert result.messages[-1]["role"] == "user"

    def test_system_message_contains_instruction(self):
        builder = PromptBuilder()
        result = builder.build(
            query="q",
            validated_chunks=[self._make_chunk("some data")],
            system_instruction="Custom instruction here.",
        )
        assert "Custom instruction here." in result.messages[0]["content"]

    def test_user_message_contains_query(self):
        builder = PromptBuilder()
        result = builder.build(
            query="Tell me about Patrick.",
            validated_chunks=[self._make_chunk("Patrick is an engineer.")],
            system_instruction="inst",
        )
        assert "Tell me about Patrick." in result.messages[-1]["content"]

    def test_evidence_numbered_in_user_message(self):
        builder = PromptBuilder()
        chunks = [
            self._make_chunk("Chunk A content."),
            self._make_chunk("Chunk B content."),
        ]
        result = builder.build(query="q", validated_chunks=chunks, system_instruction="inst")
        user_content = result.messages[-1]["content"]
        assert "[1]" in user_content
        assert "[2]" in user_content

    def test_history_injected_between_system_and_user(self):
        builder = PromptBuilder()
        history = [
            {"role": "user", "content": "first question"},
            {"role": "assistant", "content": "first answer"},
        ]
        result = builder.build(
            query="second question",
            validated_chunks=[self._make_chunk("data")],
            system_instruction="inst",
            history=history,
        )
        roles = [message["role"] for message in result.messages]
        assert roles == ["system", "user", "assistant", "user"]

    def test_empty_chunks_yields_no_evidence_in_user_message(self):
        builder = PromptBuilder()
        result = builder.build(
            query="bare question",
            validated_chunks=[],
            system_instruction="inst",
        )
        user_content = result.messages[-1]["content"]
        assert "Supporting information" not in user_content
        assert user_content == "bare question"

    def test_extra_rules_appended_to_system(self):
        builder = PromptBuilder()
        result = builder.build(
            query="q",
            validated_chunks=[self._make_chunk("data")],
            system_instruction="base",
            extra_rules=["Rule one.", "Rule two."],
        )
        system_content = result.messages[0]["content"]
        assert "Rule one." in system_content
        assert "Rule two." in system_content

    def test_voice_rule_is_present_in_system_prompt(self):
        builder = PromptBuilder()
        result = builder.build(
            query="Tell me about yourself.",
            validated_chunks=[self._make_chunk("Patrick builds backend and AI systems.")],
            system_instruction="base",
        )
        system_content = result.messages[0]["content"]
        assert "Write like a real person" in system_content
        assert "AI representative" in system_content
        assert "generic assistant closers" in system_content

    def test_scope_rule_allows_broader_personal_history_questions(self):
        builder = PromptBuilder()
        result = builder.build(
            query="Tell me about your history.",
            validated_chunks=[self._make_chunk("Patrick's background includes iOS and backend engineering.")],
            system_instruction="base",
        )
        system_content = result.messages[0]["content"]
        assert "life story" in system_content
        assert "personal history" in system_content

    def test_prompt_metrics_are_reported(self):
        builder = PromptBuilder()
        result = builder.build(
            query="Tell me about Patrick's recent backend projects.",
            validated_chunks=[self._make_chunk("Patrick built FastAPI services for internal tools.")],
            system_instruction="inst",
        )
        assert result.metrics.estimated_prompt_tokens > 0
        assert result.metrics.within_budget is True

    def test_history_is_trimmed_when_too_large(self):
        builder = PromptBuilder()
        history = [
            {"role": "user", "content": f"old question {i} " + ("x" * 200)}
            for i in range(10)
        ]
        result = builder.build(
            query="What is Patrick doing now?",
            validated_chunks=[self._make_chunk("Patrick is focused on backend and AI work.")],
            system_instruction="inst",
            history=history,
        )
        assert result.metrics.history_messages_trimmed > 0
        assert result.metrics.history_messages_used < len(history)


class TestKnowledgeCategorizer:
    def test_profile_backend_keyword_maps_to_backend(self):
        assert infer_category("Strong Python and FastAPI experience.", "profile") == "Backend"

    def test_unknown_project_keyword_uses_context_default(self):
        assert infer_category("Something unique with no matching keyword.", "projects") == "Project"


class TestContextRoutingHints:
    def test_profile_keywords_include_history_terms(self):
        keywords = _KEYWORD_HINTS["profile"]
        for expected in ("history", "story", "journey", "who are you"):
            assert expected in keywords

    def test_forced_context_prefers_projects_for_project_showcase_question(self):
        query = "Which project best shows Patrick's product and engineering skills?"
        assert _forced_context(query.lower()) == "projects"


class TestContextRouter:
    @pytest.mark.asyncio
    async def test_route_prefers_projects_for_project_showcase_question(self):
        project_chunk = KnowledgeChunk(id="proj", text="Naturalization Study App", category="projects")
        profile_chunk = KnowledgeChunk(id="prof", text="Patrick has product and engineering skills.", category="profile")

        repo = MagicMock()
        repo.get_chunks = AsyncMock(side_effect=lambda name: {
            "projects": [project_chunk],
            "profile": [profile_chunk],
            "portfolio": [],
        }.get(name, []))

        retriever = MagicMock()
        retriever.retrieve.side_effect = lambda query, chunks, top_k=3: [
            RetrievalResult(chunk=chunks[0], score=0.95 if chunks[0].category == "profile" else 0.55)
        ]

        router = ContextRouter(
            context_registry=ContextRegistry(),
            knowledge_repo=repo,
            retriever=retriever,
        )

        result = await router.route("Which project best shows Patrick's product and engineering skills?")
        assert result == "projects"


class TestKnowledgeRepository:
    def _make_pool(self, rows: list[dict]) -> MagicMock:
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

            async def __aexit__(self_, *args):
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
        await repo.reload()
        await repo.reload("profile")
