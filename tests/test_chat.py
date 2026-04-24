"""Tests for the synchronous POST /chat endpoint."""

from __future__ import annotations


# ── Happy-path ────────────────────────────────────────────────────────────────

def test_chat_returns_answer(client):
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "What are Patrick's backend skills?", "context": "profile"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "answer" in body["data"]
    assert len(body["data"]["answer"]) > 0


def test_chat_supported_flag_present(client):
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "Tell me about Patrick's education.", "context": "profile"},
    )
    assert resp.status_code == 200
    assert "supported" in resp.json()["data"]


def test_chat_meta_contains_context_and_feature(client):
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "What iOS experience does Patrick have?", "context": "profile"},
    )
    assert resp.status_code == 200
    meta = resp.json()["meta"]
    assert meta["context"] == "profile"
    assert meta["feature"] == "chat"
    assert "chunks_retrieved" in meta
    assert "chunks_validated" in meta


def test_chat_projects_context(client):
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "Tell me about the PIM project.", "context": "projects"},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_chat_auto_routes_project_showcase_question_to_projects(client):
    resp = client.post(
        "/api/v1/ai/chat",
        json={
            "message": "Which project best shows Patrick's product and engineering skills?",
            "context": "auto",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["meta"]["context"] == "projects"


def test_chat_portfolio_context(client):
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "What is in Patrick's portfolio?", "context": "portfolio"},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


# ── Session history ───────────────────────────────────────────────────────────

def test_chat_session_history_persisted(client):
    """A second turn in the same session should carry history."""
    session = "test-session-persist"

    # Turn 1
    r1 = client.post(
        "/api/v1/ai/chat",
        json={"message": "What is Patrick's name?", "context": "profile", "session_id": session},
    )
    assert r1.status_code == 200

    # Turn 2 — verify request succeeds (session store populated)
    r2 = client.post(
        "/api/v1/ai/chat",
        json={"message": "What did I just ask?", "context": "profile", "session_id": session},
    )
    assert r2.status_code == 200


def test_chat_without_session_id(client):
    """Session ID is optional; works fine when omitted."""
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "What tools does Patrick use?", "context": "profile"},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


# ── Validation ────────────────────────────────────────────────────────────────

def test_chat_empty_message_rejected(client):
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "", "context": "profile"},
    )
    assert resp.status_code == 422  # Pydantic min_length=1


def test_chat_unknown_context_returns_404(client):
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "hello", "context": "does_not_exist"},
    )
    assert resp.status_code == 404


def test_chat_missing_message_field_rejected(client):
    resp = client.post(
        "/api/v1/ai/chat",
        json={"context": "profile"},  # message field absent
    )
    assert resp.status_code == 422
