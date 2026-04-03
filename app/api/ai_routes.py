"""AI routes aggregator — combines all feature routers under /api/v1/ai."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.meta import router as meta_router
from app.api.knowledge_routes import router as knowledge_router
from app.features.chatbot.routes import router as chatbot_router
from app.features.summarizer.routes import router as summarizer_router
from app.features.suggester.routes import router as suggester_router

router = APIRouter()

router.include_router(chatbot_router, tags=["chatbot"])
router.include_router(summarizer_router, tags=["summarizer"])
router.include_router(suggester_router, tags=["suggester"])
router.include_router(meta_router, tags=["meta"])
router.include_router(knowledge_router, tags=["knowledge"])