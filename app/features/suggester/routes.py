"""Suggester routes — /suggest endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.schemas import AIRequest, AIResponse

router = APIRouter()


@router.post("/suggest", response_model=AIResponse)
async def suggest(body: AIRequest, request: Request):
    body.feature = "suggest"
    return await request.app.state.orchestrator.handle(body)
