"""Tests for the self-hosted local speech provider."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.providers.local_speech_provider import LocalSpeechProvider
from app.providers.speech_base import SpeechOptions


def _settings():
    return SimpleNamespace(
        local_tts_url="http://127.0.0.1:7861/v1/voice/synthesize",
        local_tts_api_key="local-secret",
        local_tts_reference_audio_path="C:/voice/ref.wav",
        local_tts_reference_text="This is the reference transcript.",
        local_tts_model="",
        local_tts_timeout_seconds=30.0,
        speech_chunk_size=4096,
    )


@pytest.mark.asyncio
async def test_local_speech_provider_posts_reference_voice_payload(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def aiter_bytes(self, chunk_size):
            yield b"audio-"
            yield b"bytes"

    class FakeClient:
        def __init__(self, timeout):
            captured["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        def stream(self, method, url, headers, json):
            captured["method"] = method
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr("app.providers.local_speech_provider.get_settings", _settings)
    monkeypatch.setattr("app.providers.local_speech_provider.httpx.AsyncClient", FakeClient)

    provider = LocalSpeechProvider()
    chunks = [
        chunk
        async for chunk in provider.synthesize_stream(
            "Say this locally.",
            SpeechOptions(response_format="mp3", speed=1.05),
        )
    ]

    assert b"".join(chunks) == b"audio-bytes"
    assert captured["timeout"] == 30.0
    assert captured["method"] == "POST"
    assert captured["url"] == "http://127.0.0.1:7861/v1/voice/synthesize"
    assert captured["headers"]["Authorization"] == "Bearer local-secret"
    assert captured["json"] == {
        "text": "Say this locally.",
        "response_format": "mp3",
        "reference_audio_path": "C:/voice/ref.wav",
        "reference_text": "This is the reference transcript.",
        "speed": 1.05,
    }
