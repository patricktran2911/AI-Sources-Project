"""Session store for chat history — DB-backed with in-memory fallback."""

from __future__ import annotations

import logging
from collections import deque
from threading import Lock

import asyncpg

logger = logging.getLogger(__name__)


class SessionStore:
    """Stores conversation turns per session ID.

    When a database pool is provided the store persists messages to the
    ``chat_sessions`` table.  Otherwise it falls back to an in-memory deque
    (useful for local dev / tests).
    """

    def __init__(self, max_turns: int = 5, pool: asyncpg.Pool | None = None) -> None:
        # max_turns * 2 because each turn = 1 user msg + 1 assistant msg
        self._max_messages = max_turns * 2
        self._pool = pool
        # In-memory fallback
        self._store: dict[str, deque[dict[str, str]]] = {}
        self._lock = Lock()

    # ── public API ────────────────────────────────────────────────────

    def get_history(self, session_id: str) -> list[dict[str, str]]:
        """Return prior messages for this session (empty list if new).

        NOTE: This remains synchronous because the calling code (route handlers)
        already awaits it in a non-async path.  When a pool is attached, we use
        ``asyncpg``'s sync-compatible path via ``get_history_async``.
        """
        with self._lock:
            return list(self._store.get(session_id, []))

    async def get_history_async(self, session_id: str) -> list[dict[str, str]]:
        """Async version — loads from DB when available, else falls back to memory."""
        if self._pool is not None:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT role, content FROM chat_sessions "
                    "WHERE session_id = $1 ORDER BY created_at",
                    session_id,
                )
                # Enforce max messages window
                messages = [{"role": r["role"], "content": r["content"]} for r in rows]
                return messages[-self._max_messages:]
        return self.get_history(session_id)

    def add_turn(self, session_id: str, user_msg: str, assistant_msg: str) -> None:
        """Append a user/assistant turn (in-memory only — see add_turn_async)."""
        with self._lock:
            if session_id not in self._store:
                self._store[session_id] = deque(maxlen=self._max_messages)
            self._store[session_id].append({"role": "user", "content": user_msg})
            self._store[session_id].append({"role": "assistant", "content": assistant_msg})

    async def add_turn_async(self, session_id: str, user_msg: str, assistant_msg: str) -> None:
        """Persist a turn to the database (falls back to in-memory)."""
        self.add_turn(session_id, user_msg, assistant_msg)
        if self._pool is not None:
            async with self._pool.acquire() as conn:
                await conn.executemany(
                    "INSERT INTO chat_sessions (session_id, role, content) VALUES ($1, $2, $3)",
                    [
                        (session_id, "user", user_msg),
                        (session_id, "assistant", assistant_msg),
                    ],
                )

    def clear(self, session_id: str) -> None:
        """Delete all history for a session."""
        with self._lock:
            self._store.pop(session_id, None)

    async def clear_async(self, session_id: str) -> None:
        """Delete all history for a session from both memory and DB."""
        self.clear(session_id)
        if self._pool is not None:
            async with self._pool.acquire() as conn:
                await conn.execute("DELETE FROM chat_sessions WHERE session_id = $1", session_id)
