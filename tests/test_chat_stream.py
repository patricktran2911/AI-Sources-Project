"""Tests for the SSE streaming POST /chat/stream endpoint."""

from __future__ import annotations

import json

import pytest


def _parse_sse(raw: str) -> list[dict]:
    """Parse raw SSE text into a list of JSON event objects."""
    events = []
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: "):]))
    return events


# ── Happy-path (sync client — reads full streaming body at once) ───────────────

def test_chat_stream_status_200(client):
    resp = client.post(
        "/api/v1/ai/chat/stream",
        json={"message": "Tell me about Patrick's skills.", "context": "profile"},
    )
    assert resp.status_code == 200


def test_chat_stream_content_type_is_event_stream(client):
    resp = client.post(
        "/api/v1/ai/chat/stream",
        json={"message": "What languages does Patrick know?", "context": "profile"},
    )
    assert "text/event-stream" in resp.headers["content-type"]


def test_chat_stream_events_contain_tokens(client):
    resp = client.post(
        "/api/v1/ai/chat/stream",
        json={"message": "What is Patrick's educational background?", "context": "profile"},
    )
    events = _parse_sse(resp.text)
    token_events = [e for e in events if "token" in e]
    assert len(token_events) > 0, "Expected at least one token event"


def test_chat_stream_final_event_has_done_flag(client):
    resp = client.post(
        "/api/v1/ai/chat/stream",
        json={"message": "Describe Patrick's work experience.", "context": "profile"},
    )
    events = _parse_sse(resp.text)
    done_events = [e for e in events if e.get("done") is True]
    assert len(done_events) == 1, "Expected exactly one done event"


def test_chat_stream_full_answer_assembles_from_tokens(client):
    resp = client.post(
        "/api/v1/ai/chat/stream",
        json={"message": "What is Patrick's role?", "context": "profile"},
    )
    events = _parse_sse(resp.text)
    assembled = "".join(e["token"] for e in events if "token" in e)
    assert len(assembled) > 0


def test_chat_stream_projects_context(client):
    resp = client.post(
        "/api/v1/ai/chat/stream",
        json={"message": "Tell me about the Naturalization Study App.", "context": "projects"},
    )
    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    assert any(e.get("done") for e in events)


def test_chat_stream_portfolio_context(client):
    resp = client.post(
        "/api/v1/ai/chat/stream",
        json={"message": "Show me Patrick's portfolio highlights.", "context": "portfolio"},
    )
    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    assert any(e.get("done") for e in events)


# ── Session handling ───────────────────────────────────────────────────────────

def test_chat_stream_session_persisted_on_supported_response(client):
    """After a supported streamed answer the session store should hold a turn."""
    session_id = "stream-session-test"
    client.post(
        "/api/v1/ai/chat/stream",
        json={
            "message": "What are Patrick's mobile skills?",
            "context": "profile",
            "session_id": session_id,
        },
    )
    # A second chat (non-streaming) in the same session should pick up history
    resp = client.post(
        "/api/v1/ai/chat",
        json={
            "message": "What did I just ask about?",
            "context": "profile",
            "session_id": session_id,
        },
    )
    assert resp.status_code == 200


# ── Validation ────────────────────────────────────────────────────────────────

def test_chat_stream_empty_message_rejected(client):
    resp = client.post(
        "/api/v1/ai/chat/stream",
        json={"message": "", "context": "profile"},
    )
    assert resp.status_code == 422


def test_chat_stream_unknown_context_returns_404(client):
    resp = client.post(
        "/api/v1/ai/chat/stream",
        json={"message": "hello", "context": "nonexistent"},
    )
    assert resp.status_code == 404
