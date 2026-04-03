"""Seed all JSON knowledge data as a specific user.

Usage
-----
    py -3.12 -m app.database.seed_user <user_id>

Example
-------
    py -3.12 -m app.database.seed_user patrick_tran

This reads every ``data/<context>/*.json`` file, inserts each chunk as
``user_id=<user_id>`` using ``ON CONFLICT DO NOTHING``, and prints a summary.
Global seed data (user_id=NULL) is **not** affected.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

import asyncpg

from app.core.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

_INSERT = """
INSERT INTO knowledge_chunks (id, context, text, category, metadata, user_id)
VALUES ($1, $2, $3, $4, $5, $6)
ON CONFLICT DO NOTHING;
"""


async def seed_user(user_id: str) -> None:
    """Insert all JSON seed data as *user_id*."""
    settings = get_settings()
    data_dir: Path = settings.data_dir

    if not data_dir.exists():
        logger.error("Data directory not found: %s", data_dir)
        sys.exit(1)

    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    assert pool is not None

    total = 0
    try:
        for context_dir in sorted(data_dir.iterdir()):
            if not context_dir.is_dir() or context_dir.name.startswith("."):
                continue
            if context_dir.name == "chatbot":
                continue

            context = context_dir.name
            count = 0

            for json_file in sorted(context_dir.glob("*.json")):
                items: list[dict[str, Any]] = json.loads(json_file.read_text(encoding="utf-8"))
                rows = []
                for idx, item in enumerate(items):
                    chunk_id = item.get("id", f"{json_file.stem}_{idx}")
                    rows.append((
                        f"{user_id}_{chunk_id}",
                        context,
                        item["text"],
                        item.get("category", context),
                        json.dumps(item.get("metadata", {})),
                        user_id,
                    ))

                async with pool.acquire() as conn:
                    for row in rows:
                        await conn.execute(_INSERT, *row)
                count += len(rows)

            if count:
                logger.info("  %-12s  %d chunk(s)", context, count)
                total += count

        logger.info("Seeded %d total chunk(s) for user_id='%s'", total, user_id)
    finally:
        await pool.close()


def main() -> None:
    if len(sys.argv) != 2 or not sys.argv[1].strip():
        print("Usage: py -3.12 -m app.database.seed_user <user_id>")
        sys.exit(1)
    asyncio.run(seed_user(sys.argv[1].strip()))


if __name__ == "__main__":
    main()
