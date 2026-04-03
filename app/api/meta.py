"""Meta routes — /contexts and /features listing endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.dependencies import ContextRegistryDep, FeatureRegistryDep

router = APIRouter()


@router.get("/contexts")
async def list_contexts(registry: ContextRegistryDep):
    """Return all registered context names."""
    return {"contexts": registry.list_names()}


@router.get("/features")
async def list_features(registry: FeatureRegistryDep):
    """Return all registered feature names."""
    return {"features": registry.list_names()}
