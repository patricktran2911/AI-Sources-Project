"""Summarizer routes — /summarize endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.schemas import AIRequest, AIResponse

router = APIRouter()


@router.post("/summarize", response_model=AIResponse)
async def summarize(body: AIRequest, request: Request):
    body.feature = "summarize"
    return await request.app.state.orchestrator.handle(body)
