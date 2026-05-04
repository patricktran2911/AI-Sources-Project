"""Tests for text/speech combination endpoints."""

from __future__ import annotations

import base64
import json

import pytest

from app.core.schemas import ChatResponse


class FakeSpeechProvider:
    def __init__(self) -> None:
        self.calls = []

    async def synthesize_stream(self, text, options):
        self.calls.append((text, options))
        yield b"voice-"
        yield options.response_format.encode("utf-8")


class FakeTranscriptionProvider:
    def __init__(self) -> None:
        self.calls = []

    async def transcribe(self, audio, filename, content_type=None):
        self.calls.append((audio, filename, content_type))
        return "What are Patrick's backend skills?"


@pytest.fixture()
def fake_multimodal_providers(client):
    speech = FakeSpeechProvider()
    transcription = FakeTranscriptionProvider()
    client.app.state.speech_provider = speech
    client.app.state.transcription_provider = transcription
    return speech, transcription


def test_text_to_text_alias_returns_chat_answer(client):
    resp = client.post(
        "/api/v1/ai/text-to-text",
        json={"message": "What are Patrick's backend skills?", "context": "profile"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "answer" in body["data"]


def test_text_to_speech_returns_answer_and_audio(client, fake_multimodal_providers):
    speech, _ = fake_multimodal_providers
    resp = client.post(
        "/api/v1/ai/text-to-speech",
        json={
            "message": "What are Patrick's backend skills?",
            "context": "profile",
            "response_format": "mp3",
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["answer"]
    assert base64.b64decode(body["data"]["audio"]["base64"]) == b"voice-mp3"
    assert body["data"]["audio"]["format"] == "mp3"
    assert speech.calls[0][0] == body["data"]["answer"]


def test_text_to_speech_stream_returns_sentence_audio(client, fake_multimodal_providers, monkeypatch):
    speech, _ = fake_multimodal_providers

    async def fake_chat_request(body, orchestrator, session_store):
        return ChatResponse(
            data={
                "answer": "First sentence for Patrick. Second sentence is clear.",
                "context": body.context,
            },
            meta={"context": body.context},
        )

    monkeypatch.setattr("app.api.multimodal_routes.run_chat_request", fake_chat_request)

    resp = client.post(
        "/api/v1/ai/text-to-speech/stream",
        json={
            "message": "What are Patrick's backend skills?",
            "context": "profile",
            "response_format": "mp3",
        },
    )

    assert resp.status_code == 200
    assert "application/x-ndjson" in resp.headers["content-type"]

    events = [json.loads(line) for line in resp.text.splitlines()]
    assert events[0]["type"] == "answer"
    assert events[0]["answer"] == "First sentence for Patrick. Second sentence is clear."
    assert [event["text"] for event in events if event["type"] == "audio"] == [
        "First sentence for Patrick.",
        "Second sentence is clear.",
    ]
    assert [
        base64.b64decode(event["audio"]["base64"])
        for event in events
        if event["type"] == "audio"
    ] == [b"voice-mp3", b"voice-mp3"]
    assert events[-1]["type"] == "done"
    assert [call[0] for call in speech.calls] == [
        "First sentence for Patrick.",
        "Second sentence is clear.",
    ]


def test_speech_to_text_returns_transcript(client, fake_multimodal_providers):
    _, transcription = fake_multimodal_providers
    resp = client.post(
        "/api/v1/ai/speech-to-text",
        files={"audio": ("question.wav", b"fake-audio", "audio/wav")},
    )

    assert resp.status_code == 200
    assert resp.json()["data"]["transcript"] == "What are Patrick's backend skills?"
    assert transcription.calls[0] == (b"fake-audio", "question.wav", "audio/wav")


def test_speech_to_speech_returns_transcript_answer_and_audio(client, fake_multimodal_providers):
    speech, transcription = fake_multimodal_providers
    resp = client.post(
        "/api/v1/ai/speech-to-speech",
        data={"context": "profile", "response_format": "mp3"},
        files={"audio": ("question.wav", b"fake-audio", "audio/wav")},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["transcript"] == "What are Patrick's backend skills?"
    assert body["data"]["answer"]
    assert base64.b64decode(body["data"]["audio"]["base64"]) == b"voice-mp3"
    assert speech.calls[0][0] == body["data"]["answer"]
    assert transcription.calls[0][1] == "question.wav"
