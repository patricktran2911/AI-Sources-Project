"""Repository layer — abstract knowledge storage.

Loads knowledge from local JSON files today.  Designed to be swapped out for
a database or vector DB later without touching upper layers.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.schemas import KnowledgeChunk

logger = logging.getLogger(__name__)


class KnowledgeRepository:
    """Reads knowledge chunks from JSON files under data/<context>/."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self._data_dir = data_dir or get_settings().data_dir
        self._cache: dict[str, list[KnowledgeChunk]] = {}

    # ── public API ────────────────────────────────────────────────────

    def get_chunks(self, context: str) -> list[KnowledgeChunk]:
        """Return all knowledge chunks for a given context name."""
        if context in self._cache:
            return self._cache[context]

        chunks = self._load_context(context)
        self._cache[context] = chunks
        return chunks

    def list_contexts(self) -> list[str]:
        """Return names of all available contexts (subdirectories under data/)."""
        if not self._data_dir.exists():
            return []
        return sorted(
            d.name for d in self._data_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
        )

    def reload(self, context: str | None = None) -> None:
        """Clear cache so data is re-read on next access."""
        if context:
            self._cache.pop(context, None)
        else:
            self._cache.clear()

    # ── private helpers ───────────────────────────────────────────────

    def _load_context(self, context: str) -> list[KnowledgeChunk]:
        ctx_dir = self._data_dir / context
        if not ctx_dir.is_dir():
            logger.warning("Context directory not found: %s", ctx_dir)
            return []

        chunks: list[KnowledgeChunk] = []
        for json_file in sorted(ctx_dir.glob("*.json")):
            try:
                raw: list[dict[str, Any]] = json.loads(json_file.read_text(encoding="utf-8"))
                for idx, item in enumerate(raw):
                    chunks.append(
                        KnowledgeChunk(
                            id=item.get("id", f"{json_file.stem}_{idx}"),
                            text=item["text"],
                            category=item.get("category", context),
                            metadata=item.get("metadata", {}),
                        )
                    )
            except Exception:
                logger.exception("Failed to load %s", json_file)
        logger.info("Loaded %d chunks for context '%s'", len(chunks), context)
        return chunks
