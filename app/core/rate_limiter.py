"""In-memory sliding-window rate limiter — per-IP, no external dependencies."""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock


class RateLimiter:
    """Tracks request timestamps per key and enforces a sliding-window limit."""

    def __init__(self, max_requests: int = 20, window_seconds: int = 60) -> None:
        self._max = max_requests
        self._window = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, key: str) -> bool:
        """Return True if the key is within the rate limit, False if exceeded."""
        now = time.monotonic()
        with self._lock:
            timestamps = self._hits[key]
            cutoff = now - self._window
            self._hits[key] = [t for t in timestamps if t > cutoff]
            if len(self._hits[key]) >= self._max:
                return False
            self._hits[key].append(now)
            return True

    def remaining(self, key: str) -> int:
        """Return how many requests remain in the current window."""
        now = time.monotonic()
        with self._lock:
            cutoff = now - self._window
            active = [t for t in self._hits[key] if t > cutoff]
            return max(0, self._max - len(active))
