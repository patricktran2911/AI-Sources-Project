"""Tests for the /contexts and /features meta-info endpoints."""

from __future__ import annotations


def test_list_contexts(client):
    resp = client.get("/api/v1/ai/contexts")
    assert resp.status_code == 200
    contexts = resp.json()["contexts"]
    for expected in ("general", "profile", "projects", "portfolio"):
        assert expected in contexts, f"Context '{expected}' missing: {contexts}"


def test_list_features(client):
    resp = client.get("/api/v1/ai/features")
    assert resp.status_code == 200
    assert resp.json()["features"] == ["chat"]
