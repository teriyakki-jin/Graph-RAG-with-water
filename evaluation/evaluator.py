"""
Graph RAG 시스템 벤치마크 평가기.

실행 흐름:
  1. qa_pairs.json 로드
  2. 각 질문을 RAG 시스템에 전송 (POST /api/v1/query)
  3. 응답에서 answer, contexts 추출
  4. metrics.py 지표 계산
  5. 결과 JSON + 콘솔 리포트 출력
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Optional

import httpx

from evaluation.metrics import EvalSample, MetricScores, evaluate_sample

QA_PATH = Path(__file__).parent / "qa_pairs.json"
DEFAULT_API_URL = "http://localhost:8888/api/v1/query"


async def call_rag(
    question: str,
    api_url: str,
    timeout: float = 120.0,
) -> tuple[str, list[str], Optional[str]]:
    """RAG API 호출. (answer, contexts, cypher_query) 반환."""
    payload = {"question": question, "k_vector": 4}
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(api_url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    answer = data.get("answer", "")
    vector_chunks: list[str] = data.get("vector_chunks", [])
    graph_result: str = data.get("graph_result", "") or ""
    cypher = data.get("cypher_query")

    # 컨텍스트 = 그래프 결과 + 벡터 청크
    contexts = [graph_result] + vector_chunks if graph_result else vector_chunks

    return answer, contexts, cypher


def load_qa_pairs() -> list[dict]:
    with QA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


async def run_evaluation(
    api_url: str = DEFAULT_API_URL,
    filter_category: Optional[str] = None,
    filter_difficulty: Optional[str] = None,
) -> dict:
    """전체 평가 실행. 결과 dict 반환."""
    qa_list = load_qa_pairs()

    if filter_category:
        qa_list = [q for q in qa_list if q.get("category") == filter_category]
    if filter_difficulty:
        qa_list = [q for q in qa_list if q.get("difficulty") == filter_difficulty]

    results = []
    total_start = time.perf_counter()

    for qa in qa_list:
        qid = qa["id"]
        question = qa["question"]
        print(f"  [{qid}] {question[:50]}...", end="", flush=True)

        t0 = time.perf_counter()
        try:
            answer, contexts, cypher = await call_rag(question, api_url)
            latency = time.perf_counter() - t0
            error = None
        except Exception as e:
            answer = ""
            contexts = []
            cypher = None
            latency = time.perf_counter() - t0
            error = str(e)
            print(f" ERROR: {error}")

        sample = EvalSample(
            id=qid,
            question=question,
            answer=answer,
            ground_truth=qa["ground_truth"],
            contexts=contexts,
            expected_keywords=qa.get("expected_keywords", []),
            expected_numeric=qa.get("expected_numeric"),
        )

        scores = evaluate_sample(sample)
        result_entry = {
            "id": qid,
            "category": qa.get("category"),
            "difficulty": qa.get("difficulty"),
            "question": question,
            "answer": answer,
            "ground_truth": qa["ground_truth"],
            "cypher_query": cypher,
            "latency_sec": round(latency, 3),
            "scores": scores.to_dict(),
            "error": error,
        }
        results.append(result_entry)

        if not error:
            print(f" overall={scores.overall:.2f} ({latency:.1f}s)")

    total_elapsed = time.perf_counter() - total_start

    # 집계
    valid = [r for r in results if r["error"] is None]
    aggregate = _aggregate(valid)

    report = {
        "summary": {
            "total": len(qa_list),
            "evaluated": len(valid),
            "failed": len(results) - len(valid),
            "total_time_sec": round(total_elapsed, 2),
            "avg_latency_sec": round(
                sum(r["latency_sec"] for r in valid) / max(len(valid), 1), 3
            ),
        },
        "aggregate_scores": aggregate,
        "by_category": _aggregate_by_key(valid, "category"),
        "by_difficulty": _aggregate_by_key(valid, "difficulty"),
        "results": results,
    }
    return report


def _aggregate(results: list[dict]) -> dict:
    if not results:
        return {}
    keys = ["faithfulness", "answer_relevancy", "context_precision", "keyword_recall", "numeric_accuracy", "overall"]
    agg = {}
    for k in keys:
        vals = [r["scores"][k] for r in results]
        agg[k] = round(sum(vals) / len(vals), 4)
    return agg


def _aggregate_by_key(results: list[dict], key: str) -> dict:
    groups: dict[str, list[dict]] = {}
    for r in results:
        g = r.get(key, "unknown")
        groups.setdefault(g, []).append(r)
    return {g: _aggregate(items) for g, items in sorted(groups.items())}


def print_report(report: dict) -> None:
    summary = report["summary"]
    agg = report["aggregate_scores"]

    print("\n" + "=" * 60)
    print("  Graph RAG 벤치마크 평가 결과")
    print("=" * 60)
    print(f"  평가 문항: {summary['evaluated']} / {summary['total']}")
    print(f"  실패 문항: {summary['failed']}")
    print(f"  평균 응답 시간: {summary['avg_latency_sec']:.2f}s")
    print(f"  총 소요 시간: {summary['total_time_sec']:.1f}s")
    print()
    print("  ── 종합 지표 ─────────────────────────────────────────")
    metrics_label = {
        "overall": "Overall Score     ",
        "keyword_recall": "Keyword Recall    ",
        "faithfulness": "Faithfulness      ",
        "numeric_accuracy": "Numeric Accuracy  ",
        "context_precision": "Context Precision ",
        "answer_relevancy": "Answer Relevancy  ",
    }
    for k, label in metrics_label.items():
        val = agg.get(k, 0.0)
        bar = "#" * int(val * 20) + "." * (20 - int(val * 20))
        print(f"  {label} {bar} {val:.2%}")

    print()
    print("  ── 카테고리별 Overall ────────────────────────────────")
    for cat, scores in report.get("by_category", {}).items():
        print(f"  {cat:<20} {scores.get('overall', 0):.2%}")

    print()
    print("  ── 난이도별 Overall ──────────────────────────────────")
    for diff, scores in report.get("by_difficulty", {}).items():
        print(f"  {diff:<10} {scores.get('overall', 0):.2%}")

    print()
    print("  ── 개별 결과 ─────────────────────────────────────────")
    for r in report["results"]:
        flag = "O" if not r["error"] else "X"
        overall = r["scores"]["overall"]
        kr = r["scores"]["keyword_recall"]
        na = r["scores"]["numeric_accuracy"]
        print(
            f"  {flag} [{r['id']}] {r['question'][:35]:<35} "
            f"overall={overall:.2f} kr={kr:.2f} na={na:.2f}"
        )
    print("=" * 60)


async def main(argv: list[str]) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Graph RAG Benchmark Evaluator")
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--category", default=None)
    parser.add_argument("--difficulty", default=None, choices=["easy", "medium", "hard"])
    parser.add_argument("--output", default=None, help="결과 JSON 저장 경로")
    args = parser.parse_args(argv)

    print(f"\n벤치마크 평가 시작 → {args.api_url}")
    print(f"필터: category={args.category}, difficulty={args.difficulty}\n")

    report = await run_evaluation(
        api_url=args.api_url,
        filter_category=args.category,
        filter_difficulty=args.difficulty,
    )
    print_report(report)

    output_path = args.output or str(Path(__file__).parent / "eval_result.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {output_path}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
