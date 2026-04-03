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
    user_id: str | None = Field(None, description="Optional user ID for per-user knowledge scoping")


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


# ── User Knowledge API ────────────────────────────────────────────────

class KnowledgeAddRequest(BaseModel):
    """Request body for POST /knowledge/add."""
    text: str = Field(..., min_length=1, max_length=20000, description="Raw text to store as knowledge")
    user_id: str | None = Field(None, min_length=1, max_length=128, description="Owner user ID; omit to add as global knowledge")
    context: str | None = Field(None, description="Knowledge context; auto-detected if omitted")


class KnowledgeChunkResult(BaseModel):
    """A single chunk as returned by the add/list endpoints."""
    id: str
    context: str
    category: str
    text: str


class KnowledgeAddResponse(BaseModel):
    """Response for POST /knowledge/add."""
    success: bool = True
    chunks_added: int
    contexts: list[str]
    chunks: list[KnowledgeChunkResult]


class KnowledgeListResponse(BaseModel):
    """Response for GET /knowledge/{user_id}."""
    success: bool = True
    user_id: str
    total: int
    chunks: list[KnowledgeChunkResult]


class KnowledgeDeleteResponse(BaseModel):
    """Response for DELETE /knowledge/{user_id}/{chunk_id}."""
    success: bool = True
    deleted: bool
    chunk_id: str
