"""AI routes aggregator - combines the public chatbot routers under /api/v1/ai."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.feedback_routes import router as feedback_router
from app.api.knowledge_routes import router as knowledge_router
from app.api.meta import router as meta_router
from app.features.chatbot.routes import router as chatbot_router

router = APIRouter()

router.include_router(chatbot_router, tags=["chatbot"])
router.include_router(meta_router, tags=["meta"])
router.include_router(knowledge_router, tags=["knowledge"])
router.include_router(feedback_router, tags=["feedback"])
