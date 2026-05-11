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
    parser.add_argument("--source", required=True, help="PDF/텍스트 파일 또는 디렉터리 경로")
    parser.add_argument("--batch-size", type=int, default=5, help="LLM 배치 크기 (기본: 5)")
    parser.add_argument("--skip-vector", action="store_true", help="벡터 인덱스 구축 건너뜀")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
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
