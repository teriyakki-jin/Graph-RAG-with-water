"""
수처리 도메인 Graph RAG 평가 지표.

RAGAS-inspired metrics:
  - faithfulness: 답변이 컨텍스트에 근거하는가
  - answer_relevancy: 질문과 답변의 관련성
  - context_precision: 컨텍스트의 정밀도 (정답 키워드 포함 비율)
  - numeric_accuracy: 수치 값의 정확도 (도메인 특화)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EvalSample:
    id: str
    question: str
    answer: str
    ground_truth: str
    contexts: list[str]
    expected_keywords: list[str]
    expected_numeric: Optional[dict] = None  # {"value": float, "unit": str}


@dataclass
class MetricScores:
    faithfulness: float = 0.0       # 컨텍스트 근거 비율
    answer_relevancy: float = 0.0   # 질문-답변 관련성
    context_precision: float = 0.0  # 정답 키워드 in 컨텍스트
    keyword_recall: float = 0.0     # 정답 키워드 in 답변
    numeric_accuracy: float = 0.0   # 수치 정확도
    overall: float = 0.0

    def to_dict(self) -> dict:
        return {
            "faithfulness": round(self.faithfulness, 4),
            "answer_relevancy": round(self.answer_relevancy, 4),
            "context_precision": round(self.context_precision, 4),
            "keyword_recall": round(self.keyword_recall, 4),
            "numeric_accuracy": round(self.numeric_accuracy, 4),
            "overall": round(self.overall, 4),
        }


def _tokenize_korean(text: str) -> set[str]:
    """공백·구두점 분리 토큰 집합 반환."""
    tokens = re.findall(r"[\w가-힣]+", text)
    return set(t.lower() for t in tokens if len(t) > 1)


def compute_faithfulness(answer: str, contexts: list[str]) -> float:
    """
    답변 문장 중 컨텍스트에 근거하는 비율.
    각 문장의 핵심 명사가 컨텍스트에 등장하면 '근거 있음'으로 판단.
    """
    if not contexts or not answer.strip():
        return 0.0

    sentences = [s.strip() for s in re.split(r"[.。\n]", answer) if s.strip()]
    if not sentences:
        return 0.0

    ctx_tokens = _tokenize_korean(" ".join(contexts))
    grounded = 0

    for sent in sentences:
        sent_tokens = _tokenize_korean(sent)
        if not sent_tokens:
            continue
        overlap = sent_tokens & ctx_tokens
        # 50% 이상 토큰이 컨텍스트에 있으면 근거 있음
        if len(overlap) / len(sent_tokens) >= 0.5:
            grounded += 1

    return grounded / len(sentences)


def compute_answer_relevancy(question: str, answer: str) -> float:
    """
    질문 키워드가 답변에 등장하는 비율 (precision 방식).
    Jaccard는 답변이 길수록 구조적으로 낮아지는 문제가 있어 precision으로 교체.
    """
    q_tokens = _tokenize_korean(question)
    a_tokens = _tokenize_korean(answer)
    if not q_tokens or not a_tokens:
        return 0.0
    found = sum(1 for t in q_tokens if t in a_tokens)
    return found / len(q_tokens)


def compute_context_precision(expected_keywords: list[str], contexts: list[str]) -> float:
    """
    정답 키워드 중 컨텍스트에 등장하는 비율.
    컨텍스트가 얼마나 관련 정보를 담고 있는지 측정.
    """
    if not expected_keywords or not contexts:
        return 0.0
    ctx_combined = " ".join(contexts).lower()
    found = sum(1 for kw in expected_keywords if kw.lower() in ctx_combined)
    return found / len(expected_keywords)


def compute_keyword_recall(expected_keywords: list[str], answer: str) -> float:
    """
    정답 키워드 중 실제 답변에 등장하는 비율.
    도메인 정보 회수율 (recall) 측정.
    """
    if not expected_keywords or not answer.strip():
        return 0.0
    answer_lower = answer.lower()
    found = sum(1 for kw in expected_keywords if kw.lower() in answer_lower)
    return found / len(expected_keywords)


def compute_numeric_accuracy(expected_numeric: Optional[dict], answer: str) -> float:
    """
    기대하는 수치 값이 답변에 정확히 포함되는지 확인.
    수처리 도메인에서 기준값 정확도는 핵심 지표.
    """
    if expected_numeric is None:
        return 1.0  # 수치 기대값 없으면 해당 없음 → 만점 처리

    value = expected_numeric.get("value")
    unit = expected_numeric.get("unit", "")

    if value is None:
        return 1.0

    # 숫자 표현 패턴 (0.5, 0.005, 100 등)
    numbers_in_answer = re.findall(r"\d+\.?\d*", answer)
    numbers_as_float = {float(n) for n in numbers_in_answer}

    value_found = value in numbers_as_float

    if not unit:
        return 1.0 if value_found else 0.0

    unit_found = unit.lower() in answer.lower()
    if value_found and unit_found:
        return 1.0
    elif value_found:
        return 0.7
    else:
        return 0.0


def evaluate_sample(sample: EvalSample) -> MetricScores:
    """단일 샘플에 대한 모든 지표 계산."""
    f = compute_faithfulness(sample.answer, sample.contexts)
    ar = compute_answer_relevancy(sample.question, sample.answer)
    cp = compute_context_precision(sample.expected_keywords, sample.contexts)
    kr = compute_keyword_recall(sample.expected_keywords, sample.answer)
    na = compute_numeric_accuracy(sample.expected_numeric, sample.answer)

    # 전체 점수: 가중 평균
    # keyword_recall(0.35), faithfulness(0.25), numeric_accuracy(0.20), context_precision(0.10), answer_relevancy(0.10)
    overall = (
        kr * 0.35
        + f * 0.25
        + na * 0.20
        + cp * 0.10
        + ar * 0.10
    )

    return MetricScores(
        faithfulness=f,
        answer_relevancy=ar,
        context_precision=cp,
        keyword_recall=kr,
        numeric_accuracy=na,
        overall=overall,
    )
