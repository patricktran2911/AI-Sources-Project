"""Authentication helpers for public AI endpoints."""

from __future__ import annotations

import secrets

from fastapi import Header, HTTPException

from app.core.config import get_settings


def require_api_key(
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> None:
    """Require a configured API key while allowing local/dev mode with no key."""
    expected = get_settings().app_api_key.strip()
    if not expected:
        return

    candidate = x_api_key or ""
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer":
            candidate = token

    if not secrets.compare_digest(candidate, expected):
        raise HTTPException(status_code=401, detail="Invalid API key.")
