"""AI routes aggregator - combines the public chatbot routers under /api/v1/ai."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.feedback_routes import router as feedback_router
from app.api.knowledge_routes import router as knowledge_router
from app.api.meta import router as meta_router
from app.api.multimodal_routes import router as multimodal_router
from app.api.speech_routes import router as speech_router
from app.api.voice_profile_routes import router as voice_profile_router
from app.core.security import require_api_key
from app.features.chatbot.routes import router as chatbot_router

router = APIRouter(dependencies=[Depends(require_api_key)])

router.include_router(chatbot_router, tags=["chatbot"])
router.include_router(speech_router, tags=["speech"])
router.include_router(multimodal_router, tags=["multimodal"])
router.include_router(meta_router, tags=["meta"])
router.include_router(knowledge_router, tags=["knowledge"])
router.include_router(feedback_router, tags=["feedback"])
router.include_router(voice_profile_router)
