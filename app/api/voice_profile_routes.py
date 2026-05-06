"""Voice consent/profile metadata routes."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.core.dependencies import DbPoolDep
from app.core.schemas import VoiceConsentRequest, VoiceConsentResponse, VoiceProfileResponse

router = APIRouter(prefix="/voice", tags=["voice"])

_UPSERT_PROFILE = """
INSERT INTO voice_profiles (
    user_id,
    status,
    consent_statement,
    reference_text,
    reference_audio_label,
    language
)
VALUES ($1, 'consented', $2, $3, $4, $5)
ON CONFLICT (user_id) DO UPDATE SET
    status = EXCLUDED.status,
    consent_statement = EXCLUDED.consent_statement,
    reference_text = EXCLUDED.reference_text,
    reference_audio_label = EXCLUDED.reference_audio_label,
    language = EXCLUDED.language,
    updated_at = NOW()
"""

_SELECT_PROFILE = """
SELECT user_id, status, reference_text, reference_audio_label, language
FROM voice_profiles
WHERE user_id = $1
"""


@router.post("/consent", response_model=VoiceConsentResponse)
async def record_voice_consent(body: VoiceConsentRequest, pool: DbPoolDep) -> VoiceConsentResponse:
    """Record consent metadata before enabling a user's cloned voice."""
    async with pool.acquire() as conn:
        await conn.execute(
            _UPSERT_PROFILE,
            body.user_id,
            body.consent_statement,
            body.reference_text,
            body.reference_audio_label,
            body.language,
        )

    return VoiceConsentResponse(
        user_id=body.user_id,
        reference_text=body.reference_text,
        reference_audio_label=body.reference_audio_label,
        language=body.language,
    )


@router.get("/{user_id}/profile", response_model=VoiceProfileResponse)
async def get_voice_profile(user_id: str, pool: DbPoolDep) -> VoiceProfileResponse:
    """Return non-sensitive voice profile metadata for a consented user."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(_SELECT_PROFILE, user_id)

    if row is None:
        raise HTTPException(status_code=404, detail="Voice profile not found.")

    return VoiceProfileResponse(
        user_id=row["user_id"],
        status=row["status"],
        reference_text=row["reference_text"],
        reference_audio_label=row["reference_audio_label"],
        language=row["language"],
    )


@router.get("/local-health")
async def local_voice_health() -> dict[str, object]:
    """Check whether the configured Self-Host voice service is reachable."""
    settings = get_settings()
    if settings.speech_provider.lower() != "local":
        return {"success": True, "enabled": False, "provider": settings.speech_provider}
    if not settings.local_tts_url:
        raise HTTPException(status_code=503, detail="LOCAL_TTS_URL is not configured.")

    capabilities_url = _capabilities_url(settings.local_tts_url)
    headers = {}
    if settings.local_tts_api_key:
        headers["Authorization"] = f"Bearer {settings.local_tts_api_key}"

    # Self-Host can be slow to answer while CosyVoice is warming up; a short timeout
    # produces false 503s even though the service is reachable.
    timeout = httpx.Timeout(connect=10.0, read=35.0, write=15.0, pool=10.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(capabilities_url, headers=headers)
            response.raise_for_status()
    except Exception as exc:
        detail = f"Local voice service unavailable: {exc!r}"
        raise HTTPException(status_code=503, detail=detail) from exc

    return {
        "success": True,
        "enabled": True,
        "provider": "local",
        "capabilities": response.json(),
    }


def _capabilities_url(synthesize_url: str) -> str:
    base = synthesize_url.split("/v1/", 1)[0].rstrip("/")
    return f"{base}/v1/capabilities"
