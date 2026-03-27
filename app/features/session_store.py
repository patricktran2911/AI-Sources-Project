"""In-memory session store for chat history."""

from __future__ import annotations

from collections import deque
from threading import Lock


class SessionStore:
    """Stores the last N conversation turns per session ID (thread-safe, in-memory)."""

    def __init__(self, max_turns: int = 2) -> None:
        # max_turns * 2 because each turn = 1 user msg + 1 assistant msg
        self._max_messages = max_turns * 2
        self._store: dict[str, deque[dict[str, str]]] = {}
        self._lock = Lock()

    def get_history(self, session_id: str) -> list[dict[str, str]]:
        """Return prior messages for this session (empty list if new)."""
        with self._lock:
            return list(self._store.get(session_id, []))

    def add_turn(self, session_id: str, user_msg: str, assistant_msg: str) -> None:
        """Append a user/assistant turn to the session."""
        with self._lock:
            if session_id not in self._store:
                self._store[session_id] = deque(maxlen=self._max_messages)
            self._store[session_id].append({"role": "user", "content": user_msg})
            self._store[session_id].append({"role": "assistant", "content": assistant_msg})

    def clear(self, session_id: str) -> None:
        """Delete all history for a session."""
        with self._lock:
            self._store.pop(session_id, None)
