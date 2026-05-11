"""
파이프라인 실행 순서:
  load → split → extract (LLM) → write graph → build vector index
"""
import asyncio
from pathlib import Path
from dataclasses import dataclass

from pipeline.loaders.document_loader import load_documents
from pipeline.loaders.chunker import split_documents
from pipeline.extractors.graph_extractor import build_graph_transformer, extract_graph_documents
from pipeline.graph.neo4j_writer import (
    get_neo4j_graph,
    write_graph_documents,
    build_vector_index,
    ensure_constraints,
)
from app.core.logging import setup_logging, get_logger

logger = get_logger(__name__)


@dataclass
class PipelineResult:
    source_path: str
    doc_count: int
    chunk_count: int
    node_count: int
    relationship_count: int


async def run_pipeline(
    source_path: str | Path,
    batch_size: int = 5,
    skip_vector_index: bool = False,
) -> PipelineResult:
    setup_logging()
    path = Path(source_path)
    logger.info("Pipeline started", source=str(path))

    # 1. 문서 로드
    docs = load_documents(path)
    if not docs:
        raise ValueError(f"No documents found at: {path}")

    # 2. 청크 분할
    chunks = split_documents(docs)

    # 3. Neo4j 그래프 연결 & 제약 조건
    graph = get_neo4j_graph()
    ensure_constraints(graph)

    # 4. LLM으로 엔티티/관계 추출
    transformer = build_graph_transformer()
    graph_docs = await extract_graph_documents(chunks, transformer, batch_size=batch_size)

    # 5. Neo4j 적재
    write_graph_documents(graph_docs, graph)

    # 6. 벡터 인덱스 구축 (선택)
    if not skip_vector_index:
        build_vector_index(graph)

    node_count = sum(len(g.nodes) for g in graph_docs)
    rel_count = sum(len(g.relationships) for g in graph_docs)

    result = PipelineResult(
        source_path=str(path),
        doc_count=len(docs),
        chunk_count=len(chunks),
        node_count=node_count,
        relationship_count=rel_count,
    )
    logger.info("Pipeline complete", **result.__dict__)
    return result
