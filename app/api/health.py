"""Health-check and system info routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/info")
async def info():
    s = get_settings()
    return {
        "app": s.app_name,
        "version": s.app_version,
        "llm_provider": s.llm_provider,
    }
