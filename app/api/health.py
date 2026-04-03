"""Health-check and system info routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from app.core.config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health", summary="Liveness + readiness probe")
async def health(request: Request):
    """Return service liveness status and database connectivity status.

    Returns ``200 OK`` with ``status: ok`` when the database is reachable,
    or ``200 OK`` with ``status: degraded`` when it is not (so orchestration
    layers can handle partial failures gracefully).
    """
    db_status = "ok"
    try:
        pool = request.app.state.pool
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
    except Exception as exc:
        logger.warning("Health DB probe failed: %s", exc)
        db_status = f"error: {exc}"

    overall = "ok" if db_status == "ok" else "degraded"
    return {"status": overall, "db": db_status}


@router.get("/info", summary="Application metadata")
async def info():
    """Return static application metadata: name, version, and active LLM provider."""
    s = get_settings()
    return {
        "app": s.app_name,
        "version": s.app_version,
        "llm_provider": s.llm_provider,
    }
