"""Tests for health and info endpoints."""

from __future__ import annotations


def test_health(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["db"] == "ok"


def test_info(client):
    resp = client.get("/api/v1/info")
    assert resp.status_code == 200
    data = resp.json()
    assert "app" in data
    assert "version" in data
    assert "llm_provider" in data
    assert "persona_name" in data
