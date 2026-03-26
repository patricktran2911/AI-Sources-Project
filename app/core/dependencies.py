"""Shared FastAPI dependencies."""

from app.core.config import Settings, get_settings


def get_config() -> Settings:
    """Dependency that provides application settings."""
    return get_settings()
