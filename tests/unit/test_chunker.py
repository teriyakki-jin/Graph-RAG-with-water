import pytest
from langchain_core.documents import Document

from pipeline.loaders.chunker import split_documents


def _make_doc(text: str, source: str = "test.txt") -> Document:
    return Document(page_content=text, metadata={"source": source})


def test_split_adds_chunk_metadata():
    docs = [_make_doc("가나다라마바사아자차카타파하 " * 50)]
    chunks = split_documents(docs, chunk_size=100, chunk_overlap=10)
    assert len(chunks) > 1
    for chunk in chunks:
        assert "chunk_index" in chunk.metadata
        assert "chunk_total" in chunk.metadata
        assert chunk.metadata["chunk_total"] == len(chunks)


def test_split_preserves_source_metadata():
    docs = [_make_doc("테스트 문서입니다.", source="law.pdf")]
    chunks = split_documents(docs, chunk_size=500, chunk_overlap=0)
    assert all(c.metadata["source"] == "law.pdf" for c in chunks)


def test_empty_documents_returns_empty():
    assert split_documents([]) == []
