"""evaluation/metrics.py 유닛 테스트."""

import pytest

from evaluation.metrics import (
    EvalSample,
    compute_answer_relevancy,
    compute_context_precision,
    compute_faithfulness,
    compute_keyword_recall,
    compute_numeric_accuracy,
    evaluate_sample,
)


class TestFaithfulness:
    def test_fully_grounded(self):
        answer = "탁도 기준은 0.5 NTU 이하입니다."
        contexts = ["먹는물의 탁도 기준은 0.5 NTU 이하로 규정되어 있습니다."]
        score = compute_faithfulness(answer, contexts)
        assert score > 0.5

    def test_empty_answer(self):
        assert compute_faithfulness("", ["some context"]) == 0.0

    def test_empty_contexts(self):
        assert compute_faithfulness("탁도 기준은 0.5 NTU", []) == 0.0

    def test_ungrounded_answer(self):
        answer = "외계인이 지구를 방문했다."
        contexts = ["수도법 제26조에 따라 잔류염소를 유지해야 합니다."]
        score = compute_faithfulness(answer, contexts)
        assert score < 0.5


class TestAnswerRelevancy:
    def test_relevant_answer(self):
        q = "탁도 기준은 얼마인가?"
        a = "탁도 기준은 0.5 NTU 이하입니다."
        score = compute_answer_relevancy(q, a)
        assert score > 0.2

    def test_irrelevant_answer(self):
        q = "탁도 기준은 얼마인가?"
        a = "오늘 날씨가 맑습니다."
        score = compute_answer_relevancy(q, a)
        assert score < 0.2

    def test_empty_inputs(self):
        assert compute_answer_relevancy("", "답변") == 0.0
        assert compute_answer_relevancy("질문", "") == 0.0


class TestContextPrecision:
    def test_all_keywords_in_context(self):
        kws = ["탁도", "0.5", "NTU"]
        ctx = ["먹는물 탁도 기준 0.5 NTU 이하"]
        score = compute_context_precision(kws, ctx)
        assert score == pytest.approx(1.0)

    def test_no_keywords_in_context(self):
        kws = ["페놀", "0.005"]
        ctx = ["탁도 기준에 관한 내용"]
        score = compute_context_precision(kws, ctx)
        assert score == pytest.approx(0.0)

    def test_partial_keywords(self):
        kws = ["탁도", "페놀", "잔류염소"]
        ctx = ["탁도 기준은 중요합니다."]
        score = compute_context_precision(kws, ctx)
        assert pytest.approx(score, abs=0.01) == 1 / 3


class TestKeywordRecall:
    def test_all_keywords_in_answer(self):
        kws = ["탁도", "0.5", "NTU"]
        answer = "먹는물의 탁도는 0.5 NTU 이하여야 합니다."
        score = compute_keyword_recall(kws, answer)
        assert score == pytest.approx(1.0)

    def test_no_keywords_in_answer(self):
        kws = ["페놀", "0.005"]
        answer = "탁도 기준에 관한 설명입니다."
        score = compute_keyword_recall(kws, answer)
        assert score == pytest.approx(0.0)

    def test_empty_answer(self):
        assert compute_keyword_recall(["탁도"], "") == 0.0

    def test_empty_keywords(self):
        assert compute_keyword_recall([], "어떤 답변") == 0.0


class TestNumericAccuracy:
    def test_value_and_unit_present(self):
        expected = {"value": 0.5, "unit": "NTU"}
        answer = "탁도 기준은 0.5 NTU 이하입니다."
        assert compute_numeric_accuracy(expected, answer) == 1.0

    def test_value_present_unit_missing(self):
        expected = {"value": 0.5, "unit": "NTU"}
        answer = "탁도 기준은 0.5 이하입니다."
        assert compute_numeric_accuracy(expected, answer) == pytest.approx(0.7)

    def test_value_missing(self):
        expected = {"value": 0.5, "unit": "NTU"}
        answer = "탁도 기준은 1.0 NTU 이하입니다."
        assert compute_numeric_accuracy(expected, answer) == 0.0

    def test_no_expected_numeric(self):
        assert compute_numeric_accuracy(None, "어떤 답변이든") == 1.0


class TestEvaluateSample:
    def test_perfect_answer(self):
        sample = EvalSample(
            id="T01",
            question="탁도 기준은?",
            answer="먹는물의 탁도 기준은 0.5 NTU 이하입니다.",
            ground_truth="탁도는 0.5 NTU 이하",
            contexts=["먹는물 탁도 기준은 0.5 NTU 이하로 규정됩니다."],
            expected_keywords=["탁도", "0.5", "NTU"],
            expected_numeric={"value": 0.5, "unit": "NTU"},
        )
        scores = evaluate_sample(sample)
        assert scores.overall > 0.7
        assert scores.keyword_recall == 1.0
        assert scores.numeric_accuracy == 1.0

    def test_wrong_answer(self):
        sample = EvalSample(
            id="T02",
            question="탁도 기준은?",
            answer="탁도에 대해서는 기준이 없습니다.",
            ground_truth="탁도는 0.5 NTU 이하",
            contexts=["일반 내용"],
            expected_keywords=["탁도", "0.5", "NTU"],
            expected_numeric={"value": 0.5, "unit": "NTU"},
        )
        scores = evaluate_sample(sample)
        assert scores.keyword_recall < 0.5
        assert scores.numeric_accuracy == 0.0
        assert scores.overall < 0.5
