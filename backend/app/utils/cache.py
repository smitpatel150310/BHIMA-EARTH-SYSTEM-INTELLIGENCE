import time
from typing import Any, Optional
from cachetools import TTLCache


class SimpleCache:
    """Thread-safe in-memory TTL cache wrapper."""

    def __init__(self, maxsize: int = 1000, ttl: int = 3600):
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl)

    def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)

    def set(self, key: str, value: Any) -> None:
        self._cache[key] = value

    def delete(self, key: str) -> None:
        self._cache.pop(key, None)

    def clear(self) -> None:
        self._cache.clear()

    def __contains__(self, key: str) -> bool:
        return key in self._cache


_default_cache = SimpleCache()


def get_cache() -> SimpleCache:
    return _default_cache
