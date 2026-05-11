import time
import pytest
from app.core.cache import LRUCache


def test_set_and_get():
    cache = LRUCache(max_size=3, ttl=60)
    cache.set("k", "v")
    assert cache.get("k") == "v"


def test_ttl_expiry():
    cache = LRUCache(max_size=3, ttl=0)  # 즉시 만료
    cache.set("k", "v")
    time.sleep(0.01)
    assert cache.get("k") is None


def test_lru_eviction():
    cache = LRUCache(max_size=2, ttl=60)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)  # a가 evict됨
    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_access_refreshes_order():
    cache = LRUCache(max_size=2, ttl=60)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.get("a")     # a를 최근으로 이동
    cache.set("c", 3)  # b가 evict됨
    assert cache.get("a") == 1
    assert cache.get("b") is None


def test_clear():
    cache = LRUCache()
    cache.set("x", 99)
    cache.clear()
    assert cache.get("x") is None
