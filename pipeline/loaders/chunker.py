from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# 수처리 도메인 구분자 우선순위:
# 조/항/호 → 문단 → 문장 → 단어 순으로 분할
_SEPARATORS = [
    "\n제\d+조",   # 법령 조문
    "\n\d+\.",     # 번호 목록
    "\n\n",
    "\n",
    ". ",
    " ",
    "",
]


def split_documents(
    documents: list[Document],
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size or settings.chunk_size,
        chunk_overlap=chunk_overlap or settings.chunk_overlap,
        separators=_SEPARATORS,
        is_separator_regex=True,
        length_function=len,
        keep_separator=True,
    )
    chunks = splitter.split_documents(documents)
    # 청크 순번 메타데이터 추가 (그래프 트레이서빌리티용)
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = i
        chunk.metadata["chunk_total"] = len(chunks)

    logger.info(
        "Documents split",
        original=len(documents),
        chunks=len(chunks),
        chunk_size=chunk_size or settings.chunk_size,
    )
    return chunks
