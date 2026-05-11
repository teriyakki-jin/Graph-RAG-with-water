from pathlib import Path
from typing import Sequence

from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader

from app.core.logging import get_logger

logger = get_logger(__name__)

_LOADER_MAP = {
    ".pdf": PyPDFLoader,
    ".txt": lambda path: TextLoader(path, encoding="utf-8"),
    ".docx": Docx2txtLoader,
}


def load_documents(path: str | Path) -> list[Document]:
    """파일 또는 디렉터리에서 Document 목록 반환."""
    p = Path(path)
    if p.is_file():
        return _load_file(p)
    if p.is_dir():
        docs: list[Document] = []
        for file in sorted(p.rglob("*")):
            if file.suffix.lower() in _LOADER_MAP:
                docs.extend(_load_file(file))
        logger.info("Directory loaded", path=str(p), doc_count=len(docs))
        return docs
    raise FileNotFoundError(f"Path not found: {p}")


def _load_file(file: Path) -> list[Document]:
    loader_cls = _LOADER_MAP.get(file.suffix.lower())
    if loader_cls is None:
        logger.warning("Unsupported file type, skipping", file=str(file))
        return []
    try:
        loader = loader_cls(str(file))
        docs = loader.load()
        # 출처 메타데이터 보강
        for doc in docs:
            doc.metadata.setdefault("source", str(file))
            doc.metadata.setdefault("file_name", file.name)
        logger.info("File loaded", file=file.name, pages=len(docs))
        return docs
    except Exception as e:
        logger.error("Failed to load file", file=str(file), error=str(e))
        return []
