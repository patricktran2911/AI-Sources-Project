"""Tests for the POST /speech endpoint."""

from __future__ import annotations

import pytest


class FakeSpeechProvider:
    def __init__(self) -> None:
        self.calls = []

    async def synthesize_stream(self, text, options):
        self.calls.append((text, options))
        yield b"fake-audio-"
        yield options.response_format.encode("utf-8")


@pytest.fixture()
def fake_speech_provider(client):
    provider = FakeSpeechProvider()
    client.app.state.speech_provider = provider
    return provider


def test_speech_returns_audio_stream(client, fake_speech_provider):
    resp = client.post(
        "/api/v1/ai/speech",
        json={"text": "Patrick is a backend engineer.", "response_format": "mp3"},
    )

    assert resp.status_code == 200
    assert "audio/mpeg" in resp.headers["content-type"]
    assert resp.headers["x-audio-format"] == "mp3"
    assert resp.content == b"fake-audio-mp3"
    assert fake_speech_provider.calls[0][0] == "Patrick is a backend engineer."


def test_speech_passes_voice_options_to_provider(client, fake_speech_provider):
    resp = client.post(
        "/api/v1/ai/speech",
        json={
            "text": "Speak this answer.",
            "response_format": "wav",
            "voice": "alloy",
            "instructions": "Sound relaxed and direct.",
            "speed": 1.1,
        },
    )

    assert resp.status_code == 200
    options = fake_speech_provider.calls[0][1]
    assert options.response_format == "wav"
    assert options.voice == "alloy"
    assert options.instructions == "Sound relaxed and direct."
    assert options.speed == 1.1


def test_speech_rejects_empty_text(client, fake_speech_provider):
    resp = client.post(
        "/api/v1/ai/speech",
        json={"text": "", "response_format": "mp3"},
    )

    assert resp.status_code == 422
    assert fake_speech_provider.calls == []


def test_speech_rejects_unknown_format(client, fake_speech_provider):
    resp = client.post(
        "/api/v1/ai/speech",
        json={"text": "hello", "response_format": "unknown"},
    )

    assert resp.status_code == 422
    assert fake_speech_provider.calls == []


def test_chat_answer_can_be_synthesized(client, fake_speech_provider):
    chat_resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "What are Patrick's backend skills?", "context": "profile"},
    )
    assert chat_resp.status_code == 200

    answer = chat_resp.json()["data"]["answer"]
    speech_resp = client.post(
        "/api/v1/ai/speech",
        json={"text": answer, "response_format": "mp3"},
    )

    assert speech_resp.status_code == 200
    assert fake_speech_provider.calls[0][0] == answer

