"""Suggester routes — /suggest endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.dependencies import OrchestratorDep
from app.core.schemas import AIRequest, AIResponse

router = APIRouter()


@router.post("/suggest", response_model=AIResponse)
async def suggest(body: AIRequest, orchestrator: OrchestratorDep) -> AIResponse:
    """Generate contextual suggestions using the configured LLM."""
    body.feature = "suggest"
    return await orchestrator.handle(body)
