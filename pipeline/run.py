"""
CLI 진입점.

사용법:
  python -m pipeline.run --source data/docs --batch-size 5
  python -m pipeline.run --source data/sample.pdf --skip-vector
"""
import argparse
import asyncio
import sys

from pipeline.pipeline import run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Graph RAG 데이터 파이프라인")
    sub = parser.add_subparsers(dest="command")

    # 기본 명령 (이전 방식 호환 유지)
    parser.add_argument("--source", help="PDF/텍스트 파일 또는 디렉터리 경로")
    parser.add_argument("--batch-size", type=int, default=5, help="LLM 배치 크기 (기본: 5)")
    parser.add_argument("--skip-vector", action="store_true", help="벡터 인덱스 구축 건너뜀")

    # 벡터 인덱스만 구축
    sub.add_parser("build-vector", help="기존 그래프에서 벡터 인덱스만 구축")

    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    if args.command == "build-vector":
        from pipeline.graph.neo4j_writer import get_neo4j_graph, build_vector_index
        from app.core.logging import setup_logging
        setup_logging()
        print("벡터 인덱스 구축 시작... (KR-SBERT 모델 최초 실행 시 다운로드 필요)")
        graph = get_neo4j_graph()
        build_vector_index(graph)
        print("벡터 인덱스 구축 완료 ✓")
        return

    if not args.source:
        print("오류: --source 가 필요합니다.")
        sys.exit(1)

    result = await run_pipeline(
        source_path=args.source,
        batch_size=args.batch_size,
        skip_vector_index=args.skip_vector,
    )
    print(f"\n=== 파이프라인 완료 ===")
    print(f"문서: {result.doc_count}개 → 청크: {result.chunk_count}개")
    print(f"노드: {result.node_count}개 / 관계: {result.relationship_count}개")


if __name__ == "__main__":
    asyncio.run(main())
