"""User Knowledge API - add, list, and delete per-user knowledge chunks."""

from __future__ import annotations

import logging
import re
import uuid

from fastapi import APIRouter, HTTPException

from app.contexts.knowledge_categorizer import infer_category
from app.core.dependencies import KnowledgeRepoDep, OrchestratorDep
from app.core.schemas import (
    KnowledgeAddRequest,
    KnowledgeAddResponse,
    KnowledgeChunk,
    KnowledgeChunkResult,
    KnowledgeDeleteResponse,
    KnowledgeListResponse,
)

router = APIRouter(prefix="/knowledge")
logger = logging.getLogger(__name__)

_MAX_CHUNK_CHARS = 500
_MIN_CHUNK_CHARS = 20


def _split_text(text: str) -> list[str]:
    """Split text into paragraph chunks and keep them within a reasonable size."""
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n{2,}", text)]

    chunks: list[str] = []
    for paragraph in paragraphs:
        if not paragraph:
            continue
        if len(paragraph) <= _MAX_CHUNK_CHARS:
            chunks.append(paragraph)
            continue

        sentences = re.split(r"(?<=[.!?])\s+", paragraph)
        current = ""
        for sentence in sentences:
            if current and len(current) + 1 + len(sentence) > _MAX_CHUNK_CHARS:
                chunks.append(current.strip())
                current = sentence
            else:
                current = (current + " " + sentence).strip() if current else sentence
        if current:
            chunks.append(current.strip())

    return [chunk for chunk in chunks if len(chunk) >= _MIN_CHUNK_CHARS]


@router.post("/add", response_model=KnowledgeAddResponse, summary="Add user knowledge")
async def add_knowledge(
    body: KnowledgeAddRequest,
    repo: KnowledgeRepoDep,
    orchestrator: OrchestratorDep,
) -> KnowledgeAddResponse:
    """Store user knowledge without spending extra LLM tokens for categorization."""
    raw_chunks = _split_text(body.text)
    if not raw_chunks:
        raise HTTPException(status_code=422, detail="Text is too short or contains no usable content.")

    forced_context = body.context
    results: list[KnowledgeChunkResult] = []

    for raw in raw_chunks:
        context = forced_context or await orchestrator.detect_context(raw)
        category = infer_category(raw, context)

        chunk_id = str(uuid.uuid4())
        chunk = KnowledgeChunk(id=chunk_id, text=raw, category=category)
        if body.user_id:
            await repo.add_user_chunk(chunk, context, body.user_id)
        else:
            await repo.add_global_chunk(chunk, context)

        results.append(
            KnowledgeChunkResult(id=chunk_id, context=context, category=category, text=raw)
        )

    all_contexts = sorted({result.context for result in results})
    logger.info(
        "Stored %d chunk(s) in context(s)=%s for user='%s'",
        len(results),
        all_contexts,
        body.user_id,
    )
    return KnowledgeAddResponse(
        chunks_added=len(results),
        contexts=all_contexts,
        chunks=results,
    )


@router.get("/{user_id}", response_model=KnowledgeListResponse, summary="List user knowledge")
async def list_knowledge(
    user_id: str,
    repo: KnowledgeRepoDep,
    context: str | None = None,
) -> KnowledgeListResponse:
    """Return all custom knowledge chunks owned by user_id."""
    pairs = await repo.list_user_chunks(user_id, context)
    chunk_results = [
        KnowledgeChunkResult(id=chunk.id, context=ctx, category=chunk.category, text=chunk.text)
        for ctx, chunk in pairs
    ]
    return KnowledgeListResponse(
        user_id=user_id,
        total=len(chunk_results),
        chunks=chunk_results,
    )


@router.delete(
    "/{user_id}/{chunk_id}",
    response_model=KnowledgeDeleteResponse,
    summary="Delete a knowledge chunk",
)
async def delete_knowledge(
    user_id: str,
    chunk_id: str,
    repo: KnowledgeRepoDep,
) -> KnowledgeDeleteResponse:
    """Delete a specific knowledge chunk owned by user_id."""
    deleted = await repo.delete_chunk_by_id(chunk_id, user_id)
    return KnowledgeDeleteResponse(deleted=deleted, chunk_id=chunk_id)
