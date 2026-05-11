import pytest
from pathlib import Path

from pipeline.loaders.document_loader import load_documents


def test_load_nonexistent_path_raises():
    with pytest.raises(FileNotFoundError):
        load_documents("/nonexistent/path")


def test_load_txt_file(tmp_path: Path):
    file = tmp_path / "sample.txt"
    file.write_text("수도법 제1조 목적\n이 법은 수도에 관한 사항을 규정함을 목적으로 한다.", encoding="utf-8")
    docs = load_documents(file)
    assert len(docs) == 1
    assert "수도법" in docs[0].page_content
    assert docs[0].metadata["file_name"] == "sample.txt"


def test_load_directory(tmp_path: Path):
    (tmp_path / "a.txt").write_text("문서 A", encoding="utf-8")
    (tmp_path / "b.txt").write_text("문서 B", encoding="utf-8")
    (tmp_path / "c.unknown").write_text("무시됨", encoding="utf-8")
    docs = load_documents(tmp_path)
    assert len(docs) == 2
