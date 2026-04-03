"""Repository layer — knowledge chunk persistence backed by PostgreSQL.

This is the **only** module that should contain raw SQL.  All other layers
interact with knowledge data exclusively through the public methods of
``KnowledgeRepository``.

Public API summary
------------------
Read
    get_chunks(context, user_id)         — chunks for one context + optional user scope
    list_user_chunks(user_id, context)   — all chunks owned by a user (optional context filter)
    list_contexts()                      — distinct global context names

Write (per-user)
    add_user_chunk(chunk, context, user_id)
    delete_user_chunks(context, user_id)
    get_all_user_chunks(user_id)          — (deprecated alias; prefer list_user_chunks)
    delete_chunk_by_id(chunk_id, user_id)

Write (global / admin)
    add_global_chunk(chunk, context)
"""

from __future__ import annotations

import json
import logging
from typing import NamedTuple

import asyncpg

from app.core.schemas import KnowledgeChunk

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SQL constants — kept at module level so they are easy to review and test
# ---------------------------------------------------------------------------

# Fetch chunks for a context; merges global rows with per-user rows when
# user_id is provided.
_GET_CHUNKS = """
SELECT id, context, text, category, metadata
FROM   knowledge_chunks
WHERE  context = $1
  AND  (user_id IS NULL OR user_id = $2)
ORDER BY pk;
"""

# Fetch only global (seed) chunks for a context.
_GET_CHUNKS_GLOBAL = """
SELECT id, context, text, category, metadata
FROM   knowledge_chunks
WHERE  context = $1
  AND  user_id IS NULL
ORDER BY pk;
"""

# All distinct context names that have at least one global chunk.
_LIST_CONTEXTS = """
SELECT DISTINCT context
FROM   knowledge_chunks
WHERE  user_id IS NULL
ORDER BY context;
"""

# Upsert-safe insert — silently skips duplicate (id, context) pairs.
_INSERT_CHUNK = """
INSERT INTO knowledge_chunks (id, context, text, category, metadata, user_id)
VALUES ($1, $2, $3, $4, $5, $6)
ON CONFLICT DO NOTHING;
"""

# Bulk delete all chunks owned by a user inside a specific context.
_DELETE_USER_CHUNKS = """
DELETE FROM knowledge_chunks
WHERE  context = $1 AND user_id = $2;
"""

# List every chunk owned by a user, optionally filtered to one context.
_LIST_USER_CHUNKS = """
SELECT id, context, text, category, metadata
FROM   knowledge_chunks
WHERE  user_id = $1
{context_filter}
ORDER BY pk;
"""

# Delete a single chunk that the user owns; returns the id so callers can
# detect whether a row was actually removed.
_DELETE_CHUNK_BY_ID = """
DELETE FROM knowledge_chunks
WHERE  id = $1 AND user_id = $2
RETURNING id;
"""


class KnowledgeRepository:
    """Reads and writes knowledge chunks from/to PostgreSQL.

    Instantiate once at application startup and inject via FastAPI's
    dependency system.  Never import this directly in route handlers — use
    ``KnowledgeRepoDep`` from ``app.core.dependencies`` instead.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    # ── helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _to_chunk(row: asyncpg.Record) -> KnowledgeChunk:
        """Convert a raw DB row to a ``KnowledgeChunk`` instance."""
        meta = row["metadata"]
        return KnowledgeChunk(
            id=row["id"],
            text=row["text"],
            category=row["category"],
            metadata=json.loads(meta) if isinstance(meta, str) else dict(meta),
        )

    # ── public read API ────────────────────────────────────────────────

    async def get_chunks(self, context: str, user_id: str | None = None) -> list[KnowledgeChunk]:
        """Return knowledge chunks for *context*.

        When *user_id* is provided, global chunks (user_id IS NULL) and any
        per-user chunks for that user are merged and returned together.
        When *user_id* is ``None``, only global chunks are returned.
        """
        async with self._pool.acquire() as conn:
            if user_id:
                rows = await conn.fetch(_GET_CHUNKS, context, user_id)
            else:
                rows = await conn.fetch(_GET_CHUNKS_GLOBAL, context)

        chunks = [self._to_chunk(row) for row in rows]
        logger.debug("Loaded %d chunks for context=%r user_id=%r", len(chunks), context, user_id)
        return chunks

    async def list_contexts(self) -> list[str]:
        """Return distinct context names that have at least one global chunk."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(_LIST_CONTEXTS)
        return [row["context"] for row in rows]

    async def list_user_chunks(
        self,
        user_id: str,
        context: str | None = None,
    ) -> list[tuple[str, KnowledgeChunk]]:
        """Return all chunks owned by *user_id*, ordered by insertion time.

        Args:
            user_id:  The owner of the chunks to retrieve.
            context:  Optional context name to limit results to a single context.

        Returns:
            Ordered list of ``(context_name, KnowledgeChunk)`` tuples so
            callers can group or display the context alongside each chunk.
        """
        if context:
            sql = _LIST_USER_CHUNKS.format(context_filter="AND context = $2")
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(sql, user_id, context)
        else:
            sql = _LIST_USER_CHUNKS.format(context_filter="")
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(sql, user_id)

        result = [(row["context"], self._to_chunk(row)) for row in rows]
        logger.debug("Listed %d chunk(s) for user_id=%r context=%r", len(result), user_id, context)
        return result

    async def reload(self, context: str | None = None) -> None:  # noqa: ARG002
        """No-op — the database is always the source of truth."""

    # ── per-user write API ────────────────────────────────────────────

    async def add_user_chunk(self, chunk: KnowledgeChunk, context: str, user_id: str) -> None:
        """Insert a per-user knowledge chunk (e.g. data/chatbot/{user_id}/)."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                _INSERT_CHUNK,
                chunk.id,
                context,
                chunk.text,
                chunk.category,
                json.dumps(chunk.metadata),
                user_id,
            )
        logger.info("Added chunk '%s' for user '%s' in context '%s'", chunk.id, user_id, context)

    async def add_global_chunk(self, chunk: KnowledgeChunk, context: str) -> None:
        """Insert a global knowledge chunk (user_id=NULL) — acts as admin/seed data."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                _INSERT_CHUNK,
                chunk.id,
                context,
                chunk.text,
                chunk.category,
                json.dumps(chunk.metadata),
                None,
            )
        logger.info("Added global chunk '%s' in context '%s'", chunk.id, context)

    async def delete_user_chunks(self, context: str, user_id: str) -> None:
        """Remove all per-user chunks for *user_id* in *context*."""
        async with self._pool.acquire() as conn:
            await conn.execute(_DELETE_USER_CHUNKS, context, user_id)
        logger.info("Deleted chunks for user '%s' in context '%s'", user_id, context)

    async def get_all_user_chunks(self, user_id: str) -> list[KnowledgeChunk]:
        """Return all custom chunks belonging to *user_id* across all contexts.

        Deprecated: prefer ``list_user_chunks()`` which also surfaces the
        context name per chunk.
        """
        pairs = await self.list_user_chunks(user_id)
        return [chunk for _ctx, chunk in pairs]

    async def delete_chunk_by_id(self, chunk_id: str, user_id: str) -> bool:
        """Delete a single chunk by *chunk_id* scoped to *user_id*.

        Returns True if a row was deleted, False if not found or not owned by user.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(_DELETE_CHUNK_BY_ID, chunk_id, user_id)
        deleted = row is not None
        if deleted:
            logger.info("Deleted chunk '%s' for user '%s'", chunk_id, user_id)
        return deleted
