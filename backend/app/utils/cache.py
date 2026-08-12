"""Small process-local thread-safe TTL cache for external retrieval results."""

from __future__ import annotations

from threading import RLock
from time import monotonic


class TTLCache[T]:
    def __init__(self, ttl_seconds: int, max_entries: int = 512):
        self.ttl_seconds = max(0, ttl_seconds)
        self.max_entries = max(1, max_entries)
        self._items: dict[str, tuple[float, T]] = {}
        self._lock = RLock()

    def get(self, key: str) -> T | None:
        now = monotonic()
        with self._lock:
            item = self._items.get(key)
            if item is None:
                return None
            expires_at, value = item
            if expires_at <= now:
                self._items.pop(key, None)
                return None
            return value

    def set(self, key: str, value: T) -> None:
        if self.ttl_seconds == 0:
            return
        now = monotonic()
        with self._lock:
            expired = [item_key for item_key, (expiry, _) in self._items.items() if expiry <= now]
            for item_key in expired:
                self._items.pop(item_key, None)
            if len(self._items) >= self.max_entries:
                oldest_key = min(self._items, key=lambda item_key: self._items[item_key][0])
                self._items.pop(oldest_key, None)
            self._items[key] = (now + self.ttl_seconds, value)
