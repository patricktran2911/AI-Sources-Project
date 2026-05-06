"""Tests for text/speech combination endpoints."""

from __future__ import annotations

import base64
import json

import pytest


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


def test_text_to_speech_stream_returns_live_sentence_audio(client, fake_multimodal_providers):
    speech, _ = fake_multimodal_providers
    client.post(
        "/api/v1/ai/knowledge/add",
        json={
            "user_id": "u_live_voice_stream",
            "context": "profile",
            "text": "Patrick is a full-stack engineer with skills in Python, FastAPI, and iOS development.",
        },
    )

    resp = client.post(
        "/api/v1/ai/text-to-speech/stream",
        json={
            "message": "What are Patrick's backend skills?",
            "context": "profile",
            "user_id": "u_live_voice_stream",
            "response_format": "mp3",
        },
    )

    assert resp.status_code == 200
    assert "application/x-ndjson" in resp.headers["content-type"]

    events = [json.loads(line) for line in resp.text.splitlines()]
    assert events[0]["type"] == "meta"
    answer_deltas = [event["text"] for event in events if event["type"] == "answer_delta"]
    sentence_texts = [event["text"] for event in events if event["type"] == "sentence"]
    audio_texts = [event["text"] for event in events if event["type"] == "audio"]
    assert answer_deltas
    assert answer_deltas[0].startswith("I'm") or answer_deltas[0].startswith("I ") or answer_deltas[0].startswith("My ")
    assert not answer_deltas[0].startswith("Patrick ")
    assert sentence_texts == answer_deltas
    assert audio_texts == sentence_texts
    assert [
        base64.b64decode(event["audio"]["base64"])
        for event in events
        if event["type"] == "audio"
    ] == [b"voice-mp3"] * len(audio_texts)
    assert events[-1]["type"] == "done"
    assert events[-1]["answer"] == " ".join("".join(answer_deltas).split())
    assert [call[0] for call in speech.calls] == audio_texts


def test_text_to_speech_stream_pairs_short_sentences(client, fake_multimodal_providers):
    speech, _ = fake_multimodal_providers
    original_orchestrator = client.app.state.orchestrator

    class FakeShortSentenceOrchestrator:
        def check_request(self, request):
            return None

        async def handle_stream(self, request):
            request.options["_stream_meta"] = {"supported": True}
            yield "Yes. "
            yield "I can help. "

    client.app.state.orchestrator = FakeShortSentenceOrchestrator()
    try:
        resp = client.post(
            "/api/v1/ai/text-to-speech/stream",
            json={
                "message": "Can you help?",
                "context": "profile",
                "response_format": "mp3",
            },
        )
    finally:
        client.app.state.orchestrator = original_orchestrator

    assert resp.status_code == 200
    events = [json.loads(line) for line in resp.text.splitlines()]
    sentence_events = [event for event in events if event["type"] == "sentence"]
    audio_events = [event for event in events if event["type"] == "audio"]
    assert [event["text"] for event in sentence_events] == ["Yes. I can help."]
    assert [event["sentences"] for event in sentence_events] == [["Yes.", "I can help."]]
    assert [event["text"] for event in audio_events] == ["Yes. I can help."]
    assert [call[0] for call in speech.calls] == ["Yes. I can help."]


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
