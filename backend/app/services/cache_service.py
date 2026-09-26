from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Generic, TypeVar


T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    value: T
    expires_at: float


class MemoryCache(Generic[T]):
    """Small process-local TTL cache.

    This intentionally has no persistence and is suitable for the initial
    deployment. Redis can replace this class later without changing the
    geolocation service interface.
    """

    def __init__(self, enabled: bool, ttl_seconds: int) -> None:
        self.enabled = enabled
        self.ttl_seconds = ttl_seconds
        self._items: dict[str, CacheEntry[T]] = {}

    def get(self, key: str) -> T | None:
        if not self.enabled:
            return None

        entry = self._items.get(key)

        if entry is None:
            return None

        if entry.expires_at <= time.monotonic():
            self._items.pop(key, None)
            return None

        return entry.value

    def set(self, key: str, value: T) -> None:
        if not self.enabled:
            return

        self._items[key] = CacheEntry(
            value=value,
            expires_at=time.monotonic() + self.ttl_seconds,
        )

    def clear(self) -> None:
        self._items.clear()