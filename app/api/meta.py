"""Meta routes — /contexts and /features listing endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/contexts")
async def list_contexts(request: Request):
    registry = request.app.state.context_registry
    return {"contexts": registry.list_names()}


@router.get("/features")
async def list_features(request: Request):
    registry = request.app.state.feature_registry
    return {"features": registry.list_names()}
