"""Tests for public API hardening helpers."""

from __future__ import annotations

from app.core.config import get_settings
from main import _parse_cors_origins


def test_ai_routes_require_api_key_when_configured(client):
    settings = get_settings()
    original = settings.app_api_key
    settings.app_api_key = "test-secret"
    try:
        missing = client.post(
            "/api/v1/ai/chat",
            json={"message": "What are Patrick's backend skills?", "context": "profile"},
        )
        assert missing.status_code == 401

        allowed = client.post(
            "/api/v1/ai/chat",
            headers={"Authorization": "Bearer test-secret"},
            json={"message": "What are Patrick's backend skills?", "context": "profile"},
        )
        assert allowed.status_code == 200
    finally:
        settings.app_api_key = original


def test_x_api_key_header_is_supported(client):
    settings = get_settings()
    original = settings.app_api_key
    settings.app_api_key = "header-secret"
    try:
        resp = client.post(
            "/api/v1/ai/chat",
            headers={"X-API-Key": "header-secret"},
            json={"message": "What are Patrick's backend skills?", "context": "profile"},
        )
        assert resp.status_code == 200
    finally:
        settings.app_api_key = original


def test_parse_cors_origins_ignores_empty_entries():
    assert _parse_cors_origins("https://app.example.com, ,http://localhost:8000") == [
        "https://app.example.com",
        "http://localhost:8000",
    ]
