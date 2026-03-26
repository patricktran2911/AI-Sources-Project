"""Tests for summarize and suggest feature endpoints."""

from __future__ import annotations


# ── Summarize ─────────────────────────────────────────────────────────────────

def test_summarize_returns_result(client):
    resp = client.post(
        "/api/v1/ai/summarize",
        json={"query": "Summarize Patrick's skills.", "context": "profile"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "result" in body["data"]
    assert len(body["data"]["result"]) > 0


def test_summarize_meta_context(client):
    resp = client.post(
        "/api/v1/ai/summarize",
        json={"query": "Give an overview of Patrick's projects.", "context": "projects"},
    )
    assert resp.status_code == 200
    assert resp.json()["meta"]["context"] == "projects"
    assert resp.json()["meta"]["feature"] == "summarize"


# ── Suggest ───────────────────────────────────────────────────────────────────

def test_suggest_returns_result(client):
    resp = client.post(
        "/api/v1/ai/suggest",
        json={"query": "What roles would suit Patrick?", "context": "profile"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "result" in body["data"]
    assert len(body["data"]["result"]) > 0


def test_suggest_meta_feature(client):
    resp = client.post(
        "/api/v1/ai/suggest",
        json={"query": "Suggest next projects for Patrick.", "context": "projects"},
    )
    assert resp.status_code == 200
    assert resp.json()["meta"]["feature"] == "suggest"


# ── Shared validation ─────────────────────────────────────────────────────────

def test_summarize_empty_query_rejected(client):
    resp = client.post(
        "/api/v1/ai/summarize",
        json={"query": "", "context": "profile"},
    )
    assert resp.status_code == 422


def test_suggest_unknown_context_returns_404(client):
    resp = client.post(
        "/api/v1/ai/suggest",
        json={"query": "hello", "context": "does_not_exist"},
    )
    assert resp.status_code == 404
