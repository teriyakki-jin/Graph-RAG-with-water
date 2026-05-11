import pytest
from app.services.hybrid_retriever import _build_context


def test_build_context_both_present():
    ctx = _build_context("그래프 결과", ["청크A", "청크B"])
    assert "[그래프 검색]" in ctx
    assert "[벡터 검색]" in ctx
    assert "그래프 결과" in ctx
    assert "청크A" in ctx


def test_build_context_graph_only():
    ctx = _build_context("그래프 결과", [])
    assert "[그래프 검색]" in ctx
    assert "[벡터 검색]" not in ctx


def test_build_context_vector_only():
    ctx = _build_context("", ["청크A"])
    assert "[벡터 검색]" in ctx
    assert "[그래프 검색]" not in ctx


def test_build_context_empty():
    ctx = _build_context("", [])
    assert ctx == "검색 결과 없음"


def test_build_context_truncates_chunks():
    chunks = [f"청크{i}" for i in range(10)]
    ctx = _build_context("", chunks)
    # 상위 3개만 포함되어야 함
    assert "청크0" in ctx
    assert "청크2" in ctx
    assert "청크9" not in ctx
