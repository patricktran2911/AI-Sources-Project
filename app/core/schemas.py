"""Pydantic models shared across the application."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ── API Request / Response ────────────────────────────────────────────

class AIRequest(BaseModel):
    """Shared input for all AI feature endpoints."""
    query: str = Field(..., min_length=1, max_length=4000, description="User query")
    context: str = Field("general", description="Context name (profile, projects, portfolio, …)")
    feature: str = Field("chat", description="Feature name (chat, summarize, suggest, …)")
    options: dict[str, Any] = Field(default_factory=dict, description="Extra options per feature")


class AIResponse(BaseModel):
    """Standardised JSON envelope returned by every endpoint."""
    success: bool = True
    data: dict[str, Any] = Field(default_factory=dict)
    meta: dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    """Dedicated request shape for the /chat endpoint."""
    message: str = Field(..., min_length=1, max_length=4000, description="User message")
    context: str = Field("auto", description="Context name, or 'auto' to detect automatically")
    session_id: str | None = Field(None, description="Optional session ID for chat history")


class ChatResponse(BaseModel):
    """Response shape for the /chat endpoint."""
    success: bool = True
    data: dict[str, Any] = Field(default_factory=dict)   # answer, supported
    meta: dict[str, Any] = Field(default_factory=dict)


# ── Internal data transfer objects ────────────────────────────────────

class KnowledgeChunk(BaseModel):
    """A single piece of knowledge stored in the data layer."""
    id: str
    text: str
    category: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    """A chunk scored after semantic retrieval."""
    chunk: KnowledgeChunk
    score: float = 0.0


class RerankResult(BaseModel):
    """A chunk scored after cross-encoder reranking."""
    chunk: KnowledgeChunk
    score: float = 0.0
