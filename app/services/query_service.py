"""
다단계 추론이 필요한 질의 처리.

단순 질의:  hybrid_query 한 번으로 처리
복합 질의:  질문을 서브쿼리로 분해 → 각각 검색 → 결합하여 최종 답변
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.config import settings
from app.core.logging import get_logger
from app.services.hybrid_retriever import hybrid_query, HybridAnswer

if TYPE_CHECKING:
    from langchain_neo4j import Neo4jGraph

logger = get_logger(__name__)

_DECOMPOSE_PROMPT = """다음 질문을 독립적인 서브 질문 2~4개로 분해하세요.
각 서브 질문은 단독으로 검색 가능해야 합니다.
응답 형식 (줄바꿈으로 구분):
1. 서브 질문1
2. 서브 질문2
...

질문: {question}"""


_COMPLEX_KEYWORDS = frozenset([
    # 비교·분석 의도
    "차이", "비교", "공통점", "장단점",
    # 인과·설명 의도
    "이유", "왜", "원인", "어떻게",
    # 원리·메커니즘 설명 의도
    "원리", "메커니즘", "설명하라", "서술",
    # 다단계·절차 의도
    "과정", "절차", "단계", "순서",
    # 범위 전체 열거 의도
    "모두", "전체", "목록", "종류",
])
_COMPLEX_LENGTH_THRESHOLD = 80

# 멀티홉: 두 개 이상의 개체 간 연결·비교를 요구하는 질의
_MULTIHOP_KEYWORDS = frozenset([
    "연결", "흐름", "관계", "연관", "거쳐",
    "비교", "차이", "같은가", "다른가",
    "함께", "동시에", "대비", "vs",
    "원리", "메커니즘",
])
_K_VECTOR_MULTIHOP = 8


def _is_complex(question: str) -> bool:
    """복합 질의 여부 판단.

    키워드 기반: 비교·인과·절차·전체 열거 의도가 포함된 질의는 서브쿼리 분해 필요.
    길이 기반: 80자 초과는 단일 홉 검색으로 커버하기 어려운 복합 조건일 가능성이 높음.
    """
    return (
        any(kw in question for kw in _COMPLEX_KEYWORDS)
        or len(question) > _COMPLEX_LENGTH_THRESHOLD
    )


def _is_multihop(question: str) -> bool:
    """멀티홉 질의 여부: 두 개체 간 연결·비교를 탐색하는 질의."""
    return any(kw in question for kw in _MULTIHOP_KEYWORDS)


async def _decompose_question(question: str) -> list[str]:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage
    llm = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key,
        temperature=0,
        max_tokens=512,
    )
    messages = [HumanMessage(content=_DECOMPOSE_PROMPT.format(question=question))]
    response = await llm.ainvoke(messages)
    lines = [
        line.lstrip("0123456789. ").strip()
        for line in response.content.strip().splitlines()
        if line.strip() and line[0].isdigit()
    ]
    return lines if lines else [question]


_SYNTHESIZE_SYSTEM = """당신은 수처리 분야 전문가입니다. 아래 서브 답변들을 통합해 원래 질문에 최종 답변하세요.

[절대 규칙]
- 오직 서브 답변에 명시된 정보만 사용하세요. 사전 학습 지식은 절대 추가하지 마세요.
- 서브 답변에 없는 정보는 추측하거나 보완하지 말고 "해당 정보를 찾을 수 없습니다"라고 답하세요.
- 수치/기준값은 반드시 출처(법령명 또는 문서명)를 명시하세요.

[비교 질문 형식]
두 대상을 비교하는 질문은 반드시 아래 형식으로 답하세요:

[대상A]
- 특성1: (서브 답변에 있는 내용만)
- 특성2: ...

[대상B]
- 특성1: (서브 답변에 있는 내용만)
- 특성2: ...

핵심 차이: (서브 답변에서 도출된 차이점만)

[연결·흐름 질문]
단계적 연결 관계를 명확히 서술하세요."""


async def _synthesize(question: str, sub_answers: list[HybridAnswer]) -> str:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage
    llm = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key,
        temperature=0.1,
        max_tokens=1024,
    )
    parts = "\n\n".join(
        f"서브 답변 {i+1}:\n{a.answer}" for i, a in enumerate(sub_answers)
    )
    messages = [
        SystemMessage(content=_SYNTHESIZE_SYSTEM),
        HumanMessage(content=f"원래 질문: {question}\n\n{parts}"),
    ]
    response = await llm.ainvoke(messages)
    return response.content


async def process_query(question: str, graph: "Neo4jGraph", k_vector: int = 4) -> HybridAnswer:
    """질의 복잡도를 판단하여 단순/다단계 처리 분기."""
    effective_k = _K_VECTOR_MULTIHOP if _is_multihop(question) else k_vector

    if not _is_complex(question):
        logger.info("Simple query", question=question[:60])
        return await hybrid_query(question, graph, k_vector=effective_k)

    logger.info("Complex query - decomposing", question=question[:60])
    sub_questions = await _decompose_question(question)
    logger.info("Sub-questions", count=len(sub_questions), questions=sub_questions)

    import asyncio
    results = await asyncio.gather(
        *[hybrid_query(sq, graph, k_vector=effective_k) for sq in sub_questions],
        return_exceptions=True,
    )
    sub_answers = [r for r in results if isinstance(r, HybridAnswer)]

    if not sub_answers:
        logger.warning("All sub-queries failed, falling back to simple query")
        return await hybrid_query(question, graph, k_vector=effective_k)

    final_answer = await _synthesize(question, sub_answers)
    all_sources = list({s for a in sub_answers for s in a.sources})
    all_chunks = [chunk for a in sub_answers for chunk in a.vector_chunks]

    return HybridAnswer(
        answer=final_answer,
        graph_result=sub_answers[0].graph_result,
        vector_chunks=all_chunks,
        cypher_query=sub_answers[0].cypher_query,
        sources=all_sources,
    )
