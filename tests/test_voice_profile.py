"""Tests for consented voice profile metadata routes."""

from __future__ import annotations

from app.api.voice_profile_routes import _capabilities_url


def test_record_and_read_voice_consent(client):
    payload = {
        "user_id": "patrick",
        "consent_accepted": True,
        "consent_statement": "I consent to use my own voice for this personal AI chatbot.",
        "reference_text": "This is the exact text spoken in my approved reference audio sample.",
        "reference_audio_label": "patrick_voice_sample.wav",
        "language": "en",
    }

    consent = client.post("/api/v1/ai/voice/consent", json=payload)
    assert consent.status_code == 200
    assert consent.json()["status"] == "consented"

    profile = client.get("/api/v1/ai/voice/patrick/profile")
    assert profile.status_code == 200
    body = profile.json()
    assert body["user_id"] == "patrick"
    assert body["status"] == "consented"
    assert body["reference_audio_label"] == "patrick_voice_sample.wav"


def test_voice_consent_requires_explicit_voice_consent(client):
    resp = client.post(
        "/api/v1/ai/voice/consent",
        json={
            "user_id": "patrick",
            "consent_accepted": True,
            "consent_statement": "I agree to the general terms.",
            "reference_text": "This is the exact text spoken in my approved reference audio sample.",
        },
    )

    assert resp.status_code == 422


def test_unknown_voice_profile_returns_404(client):
    resp = client.get("/api/v1/ai/voice/not-created/profile")
    assert resp.status_code == 404


def test_capabilities_url_targets_self_host_capabilities():
    assert (
        _capabilities_url("http://127.0.0.1:7861/v1/voice/synthesize")
        == "http://127.0.0.1:7861/v1/capabilities"
    )
