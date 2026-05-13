"""
누락된 문서를 벡터 인덱스에 직접 추가.
LLM 그래프 추출 없이 Document 노드만 생성 → 벡터 검색 보강.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path

from pipeline.loaders.document_loader import load_documents
from pipeline.loaders.chunker import split_documents
from pipeline.graph.neo4j_writer import get_neo4j_graph, get_embeddings, build_vector_index
from app.core.logging import setup_logging, get_logger
from app.core.config import settings

setup_logging()
logger = get_logger(__name__)


def ingest_to_vector(file_paths: list[str]) -> None:
    graph = get_neo4j_graph()
    embeddings = get_embeddings()

    all_chunks = []
    for fp in file_paths:
        p = Path(fp)
        docs = load_documents(p)
        chunks = split_documents(docs)
        print(f"  {p.name}: {len(docs)}개 문서 → {len(chunks)}개 청크")
        all_chunks.extend(chunks)

    print(f"\n총 {len(all_chunks)}개 청크를 Neo4j Document 노드로 적재...")

    # Document 노드를 직접 Neo4j에 MERGE
    for i, chunk in enumerate(all_chunks):
        doc_id = f"{chunk.metadata.get('source', 'unknown')}_{chunk.metadata.get('chunk_index', i)}"
        source = chunk.metadata.get("source", "")
        graph.query(
            """
            MERGE (d:Document {id: $id})
            SET d.text = $text, d.source = $source
            """,
            {"id": doc_id, "text": chunk.page_content, "source": source}
        )

    print(f"{len(all_chunks)}개 Document 노드 적재 완료")
    print("\n벡터 인덱스 재구축 중...")
    build_vector_index(graph)
    print("벡터 인덱스 재구축 완료")


def add_thm_graph_nodes() -> None:
    """THM 수질기준 및 NOM 관계 노드 직접 추가."""
    graph = get_neo4j_graph()

    graph.query("""
        MERGE (thm:__Entity__ {id: '총트리할로메탄'})
        MERGE (std:__Entity__ {id: '0.1 mg/L 이하'})
        MERGE (thm)-[:기준값이다]->(std)
    """)

    graph.query("""
        MERGE (nom:__Entity__ {id: '자연유기물'})
        MERGE (thm:__Entity__ {id: '총트리할로메탄'})
        MERGE (nom)-[:생성한다]->(thm)
    """)

    graph.query("""
        MERGE (nom:__Entity__ {id: '자연유기물'})
        MERGE (haa:__Entity__ {id: '할로아세틱산'})
        MERGE (nom)-[:생성한다]->(haa)
    """)

    graph.query("""
        MERGE (brom:__Entity__ {id: '브롬화물'})
        MERGE (bthm:__Entity__ {id: '브롬계 THM'})
        MERGE (brom)-[:생성한다]->(bthm)
    """)

    graph.query("""
        MERGE (ozone:__Entity__ {id: '오존 소독'})
        MERGE (bro3:__Entity__ {id: '브로모산염'})
        MERGE (bro3std:__Entity__ {id: '0.01 mg/L 이하'})
        MERGE (ozone)-[:생성한다]->(bro3)
        MERGE (bro3)-[:기준값이다]->(bro3std)
    """)

    print("THM 관련 그래프 노드 추가 완료")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--thm", action="store_true", help="THM 데이터 보강")
    args = parser.parse_args()

    if args.thm:
        targets = ["data/docs/THM_소독부산물.txt"]
        label = "THM 소독부산물"
    else:
        targets = ["data/docs/수질사고_처벌규정.txt"]
        label = "누락 문서"

    print(f"=== {label} 벡터 인덱스 보강 ===")
    for t in targets:
        if not Path(t).exists():
            print(f"  파일 없음: {t}")
            sys.exit(1)
    ingest_to_vector(targets)

    if args.thm:
        add_thm_graph_nodes()

    print("\n완료. 서버 재시작 후 평가를 실행하세요.")
