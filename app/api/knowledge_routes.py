"""User Knowledge API — add, list, and delete per-user knowledge chunks."""

from __future__ import annotations

import logging
import re
import uuid

from fastapi import APIRouter, HTTPException

from app.core.dependencies import KnowledgeRepoDep, OrchestratorDep, ProviderDep
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

# ── text chunking ─────────────────────────────────────────────────────

_MAX_CHUNK_CHARS = 500
_MIN_CHUNK_CHARS = 20


def _split_text(text: str) -> list[str]:
    """Split *text* into paragraph-level chunks, then split long paragraphs
    further at sentence boundaries.  Strips blank segments.
    """
    # Primary split: blank lines
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text)]

    chunks: list[str] = []
    for para in paragraphs:
        if not para:
            continue
        if len(para) <= _MAX_CHUNK_CHARS:
            chunks.append(para)
        else:
            # Split long paragraphs at sentence endings
            sentences = re.split(r"(?<=[.!?])\s+", para)
            current = ""
            for sent in sentences:
                if current and len(current) + 1 + len(sent) > _MAX_CHUNK_CHARS:
                    chunks.append(current.strip())
                    current = sent
                else:
                    current = (current + " " + sent).strip() if current else sent
            if current:
                chunks.append(current.strip())

    return [c for c in chunks if len(c) >= _MIN_CHUNK_CHARS]


# ── endpoints ─────────────────────────────────────────────────────────

@router.post("/add", response_model=KnowledgeAddResponse, summary="Add user knowledge")
async def add_knowledge(
    body: KnowledgeAddRequest,
    repo: KnowledgeRepoDep,
    provider: ProviderDep,
    orchestrator: OrchestratorDep,
) -> KnowledgeAddResponse:
    """Receive free-form text, auto-detect (or use supplied) context, split into
    chunks, generate a category label for each chunk via the LLM, and persist
    everything as per-user knowledge in the database.

    When ``context`` is provided, all chunks are forced into that context.
    When omitted, each chunk is routed individually via the orchestrator.
    """
    # 1. Chunk the input text
    raw_chunks = _split_text(body.text)
    if not raw_chunks:
        raise HTTPException(status_code=422, detail="Text is too short or contains no usable content.")

    # 2. Resolve context — either forced or per-chunk auto-detect
    forced_context = body.context  # None when caller wants auto-detect

    # 3. Persist each chunk (context + category resolved per-chunk)
    results: list[KnowledgeChunkResult] = []
    for raw in raw_chunks:
        # Context
        if forced_context:
            context = forced_context
        else:
            context = await orchestrator.detect_context(raw)

        # Ask LLM for a short category label (2–4 words)
        try:
            category = await provider.generate(
                [{"role": "user", "content": f"Classify the following text with a short label of 2-4 words (no explanation, just the label):\n\n{raw}"}],
                max_tokens=20,
            )
            category = category.strip().strip("\"'").strip()
        except Exception:
            logger.warning("Category generation failed for chunk, using 'general'", exc_info=True)
            category = "general"

        chunk_id = str(uuid.uuid4())
        chunk = KnowledgeChunk(id=chunk_id, text=raw, category=category)
        if body.user_id:
            await repo.add_user_chunk(chunk, context, body.user_id)
        else:
            await repo.add_global_chunk(chunk, context)
        results.append(KnowledgeChunkResult(id=chunk_id, context=context, category=category, text=raw))

    all_contexts = sorted({r.context for r in results})
    logger.info(
        "Stored %d chunk(s) in context(s)=%s for user='%s'",
        len(results), all_contexts, body.user_id,
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
    """Return all custom knowledge chunks owned by *user_id*.
    Optionally filter by *context* query parameter (e.g. ``?context=profile``).
    """
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


@router.delete("/{user_id}/{chunk_id}", response_model=KnowledgeDeleteResponse, summary="Delete a knowledge chunk")
async def delete_knowledge(
    user_id: str,
    chunk_id: str,
    repo: KnowledgeRepoDep,
) -> KnowledgeDeleteResponse:
    """Delete a specific knowledge chunk owned by *user_id*."""
    deleted = await repo.delete_chunk_by_id(chunk_id, user_id)
    return KnowledgeDeleteResponse(deleted=deleted, chunk_id=chunk_id)
