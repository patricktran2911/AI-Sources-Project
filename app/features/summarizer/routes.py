"""Summarizer routes — /summarize endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.dependencies import OrchestratorDep
from app.core.schemas import AIRequest, AIResponse

router = APIRouter()


@router.post("/summarize", response_model=AIResponse)
async def summarize(body: AIRequest, orchestrator: OrchestratorDep) -> AIResponse:
    """Summarize a document or passage using the configured LLM."""
    body.feature = "summarize"
    return await orchestrator.handle(body)
