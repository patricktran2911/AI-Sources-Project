"""Database migrations and JSON seed loader.

run_migrations(pool)  — creates the knowledge_chunks table and indexes (idempotent).
seed_from_json(pool, data_dir) — loads all JSON files under data/ into the DB,
    skipping rows that already exist (ON CONFLICT DO NOTHING).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS knowledge_chunks (
    pk          BIGSERIAL PRIMARY KEY,
    id          TEXT        NOT NULL,
    context     TEXT        NOT NULL,
    text        TEXT        NOT NULL,
    category    TEXT        NOT NULL DEFAULT '',
    metadata    JSONB       NOT NULL DEFAULT '{}',
    user_id     TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

# Unique index for global chunks (user_id IS NULL)
_IDX_GLOBAL = """
CREATE UNIQUE INDEX IF NOT EXISTS uq_chunks_global
    ON knowledge_chunks (id, context)
    WHERE user_id IS NULL;
"""

# Unique index for per-user chunks (user_id IS NOT NULL)
_IDX_USER = """
CREATE UNIQUE INDEX IF NOT EXISTS uq_chunks_user
    ON knowledge_chunks (id, context, user_id)
    WHERE user_id IS NOT NULL;
"""

# Index to speed up lookups by context + user_id
_IDX_LOOKUP = """
CREATE INDEX IF NOT EXISTS idx_chunks_context_user
    ON knowledge_chunks (context, user_id);
"""

_INSERT = """
INSERT INTO knowledge_chunks (id, context, text, category, metadata, user_id)
VALUES ($1, $2, $3, $4, $5, $6)
ON CONFLICT DO NOTHING;
"""


async def run_migrations(pool: asyncpg.Pool) -> None:
    """Apply DDL statements — safe to run on every startup."""
    async with pool.acquire() as conn:
        await conn.execute(_CREATE_TABLE)
        await conn.execute(_IDX_GLOBAL)
        await conn.execute(_IDX_USER)
        await conn.execute(_IDX_LOOKUP)
    logger.info("Database migrations applied")


async def seed_from_json(pool: asyncpg.Pool, data_dir: Path) -> None:
    """Seed knowledge_chunks from all JSON files under data_dir.<context>/*.json.

    Only global chunks (user_id=NULL) are seeded here.
    Per-user data (data/chatbot/<user_id>/) is written at runtime via the API.
    Rows that already exist are silently skipped (ON CONFLICT DO NOTHING).
    """
    if not data_dir.exists():
        logger.warning("data_dir not found, skipping JSON seed: %s", data_dir)
        return

    total = 0
    for context_dir in sorted(data_dir.iterdir()):
        if not context_dir.is_dir() or context_dir.name.startswith("."):
            continue
        # Skip the chatbot directory — per-user data is not seeded from files
        if context_dir.name == "chatbot":
            continue

        context = context_dir.name
        rows: list[tuple[str, str, str, str, str, None]] = []

        for json_file in sorted(context_dir.glob("*.json")):
            try:
                items: list[dict[str, Any]] = json.loads(json_file.read_text(encoding="utf-8"))
                for idx, item in enumerate(items):
                    chunk_id = item.get("id", f"{json_file.stem}_{idx}")
                    rows.append((
                        chunk_id,
                        context,
                        item["text"],
                        item.get("category", context),
                        json.dumps(item.get("metadata", {})),
                        None,  # user_id = NULL → global chunk
                    ))
            except Exception:
                logger.exception("Failed to read seed file: %s", json_file)

        if rows:
            async with pool.acquire() as conn:
                await conn.executemany(_INSERT, rows)
            logger.info("Seeded %d chunks for context '%s'", len(rows), context)
            total += len(rows)

    logger.info("JSON seed complete — %d total chunks inserted (duplicates skipped)", total)
