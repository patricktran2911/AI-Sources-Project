"""Speech routes - text-to-speech support endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
from app.core.dependencies import SpeechProviderDep
from app.core.schemas import SpeechRequest
from app.providers.speech_base import SpeechOptions

router = APIRouter()

MEDIA_TYPES = {
    "mp3": "audio/mpeg",
    "opus": "audio/ogg",
    "aac": "audio/aac",
    "flac": "audio/flac",
    "wav": "audio/wav",
    "pcm": "audio/pcm",
}


@router.post(
    "/speech",
    responses={
        200: {
            "content": {
                "audio/mpeg": {},
                "audio/ogg": {},
                "audio/aac": {},
                "audio/flac": {},
                "audio/wav": {},
                "audio/pcm": {},
            },
            "description": "Streaming audio generated from the supplied text.",
        }
    },
)
async def speech(body: SpeechRequest, speech_provider: SpeechProviderDep):
    """Stream synthesized speech audio for an existing chatbot answer."""
    options = SpeechOptions(
        response_format=body.response_format,
        voice=body.voice,
        instructions=body.instructions,
        speed=body.speed,
    )
    media_type = MEDIA_TYPES[body.response_format]
    settings = get_settings()

    return StreamingResponse(
        speech_provider.synthesize_stream(body.text, options),
        media_type=media_type,
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'inline; filename="chatbot-speech.{body.response_format}"',
            "X-Audio-Provider": settings.speech_provider,
            "X-Audio-Format": body.response_format,
        },
    )

