"""
인메모리 LRU 캐시.
- 질의 응답 캐싱 (동일 질문 재요청 시 LLM 비용 절감)
- TTL: 1시간 (수처리 규정은 자주 바뀌지 않음)
"""
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

_TTL_SECONDS = 3600
_MAX_SIZE = 128


@dataclass
class _Entry:
    value: Any
    expires_at: float


class LRUCache:
    def __init__(self, max_size: int = _MAX_SIZE, ttl: int = _TTL_SECONDS) -> None:
        self._store: OrderedDict[str, _Entry] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.monotonic() > entry.expires_at:
            del self._store[key]
            return None
        self._store.move_to_end(key)
        return entry.value

    def set(self, key: str, value: Any) -> None:
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = _Entry(value=value, expires_at=time.monotonic() + self._ttl)
        if len(self._store) > self._max_size:
            self._store.popitem(last=False)

    def clear(self) -> None:
        self._store.clear()


query_cache = LRUCache()
