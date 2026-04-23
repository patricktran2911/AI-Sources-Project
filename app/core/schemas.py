"""Pydantic models shared across the application."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.core.config import get_settings


def _normalize_query(value: str, field_name: str) -> str:
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty.")
    limit = get_settings().max_user_query_chars
    if len(cleaned) > limit:
        raise ValueError(f"{field_name} exceeds the {limit}-character safety limit.")
    return cleaned


class AIRequest(BaseModel):
    """Shared input for all AI feature endpoints."""

    query: str = Field(..., min_length=1, description="User query")
    context: str = Field("general", description="Context name (profile, projects, portfolio, ...)")
    feature: str = Field("chat", description="Feature name (chat)")
    options: dict[str, Any] = Field(default_factory=dict, description="Extra options per feature")

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        return _normalize_query(value, "Query")


class AIResponse(BaseModel):
    """Standardized JSON envelope returned by every endpoint."""

    success: bool = True
    data: dict[str, Any] = Field(default_factory=dict)
    meta: dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    """Dedicated request shape for the /chat endpoint."""

    message: str = Field(..., min_length=1, description="User message")
    context: str = Field("auto", description="Context name, or 'auto' to detect automatically")
    session_id: str | None = Field(None, description="Optional session ID for chat history")
    user_id: str | None = Field(None, description="Optional user ID for per-user knowledge scoping")

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        return _normalize_query(value, "Message")


class ChatResponse(BaseModel):
    """Response shape for the /chat endpoint."""

    success: bool = True
    data: dict[str, Any] = Field(default_factory=dict)
    meta: dict[str, Any] = Field(default_factory=dict)


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


class FeedbackRequest(BaseModel):
    """Request body for POST /feedback."""

    session_id: str | None = Field(None, description="Session the feedback relates to")
    query: str = Field(..., min_length=1, description="Original user query")
    answer: str = Field(..., min_length=1, description="AI answer being rated")
    rating: str = Field(..., pattern=r"^(thumbs_up|thumbs_down)$", description="thumbs_up or thumbs_down")
    comment: str | None = Field(None, max_length=2000, description="Optional free-text comment")
    context: str | None = Field(None, description="Context used for the response")
    feature: str | None = Field(None, description="Feature used for the response")

    @field_validator("query")
    @classmethod
    def validate_feedback_query(cls, value: str) -> str:
        return _normalize_query(value, "Query")


class FeedbackResponse(BaseModel):
    """Response for POST /feedback."""

    success: bool = True
    message: str = "Feedback recorded"
