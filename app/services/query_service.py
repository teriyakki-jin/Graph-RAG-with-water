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


def _is_complex(question: str) -> bool:
    """복합 질의 판단: 비교/원인/단계/여러 엔티티 포함 여부."""
    keywords = ["차이", "비교", "이유", "왜", "과정", "절차", "단계", "모두", "전체"]
    return any(kw in question for kw in keywords) or len(question) > 80


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
        SystemMessage(content="당신은 수처리 전문가입니다. 아래 서브 답변들을 통합해 원래 질문에 최종 답변하세요."),
        HumanMessage(content=f"원래 질문: {question}\n\n{parts}"),
    ]
    response = await llm.ainvoke(messages)
    return response.content


async def process_query(question: str, graph: "Neo4jGraph") -> HybridAnswer:
    """질의 복잡도를 판단하여 단순/다단계 처리 분기."""
    if not _is_complex(question):
        logger.info("Simple query", question=question[:60])
        return await hybrid_query(question, graph)

    logger.info("Complex query — decomposing", question=question[:60])
    sub_questions = await _decompose_question(question)
    logger.info("Sub-questions", count=len(sub_questions), questions=sub_questions)

    import asyncio
    sub_answers = await asyncio.gather(
        *[hybrid_query(sq, graph) for sq in sub_questions],
        return_exceptions=False,
    )

    final_answer = await _synthesize(question, list(sub_answers))
    all_sources = list({s for a in sub_answers for s in a.sources})
    all_chunks = [chunk for a in sub_answers for chunk in a.vector_chunks]

    return HybridAnswer(
        answer=final_answer,
        graph_result=sub_answers[0].graph_result if sub_answers else "",
        vector_chunks=all_chunks,
        cypher_query=sub_answers[0].cypher_query if sub_answers else None,
        sources=all_sources,
    )
