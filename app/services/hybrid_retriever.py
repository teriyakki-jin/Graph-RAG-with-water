"""
하이브리드 검색 전략:
  - 그래프 검색: 구조화된 관계 탐색 (Cypher) → 정밀한 사실 조회
  - 벡터 검색: 의미 유사도 기반 청크 → 서술형 맥락 보완
  - 통합: 두 결과를 컨텍스트로 합쳐 LLM에 최종 답변 요청
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.core.config import settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    from langchain_neo4j import Neo4jGraph

from app.services.vector_retriever import vector_search

logger = get_logger(__name__)

_SYSTEM_PROMPT = """당신은 수처리 분야 전문가 AI입니다.
아래에 두 가지 검색 결과가 제공됩니다:
1. [그래프 검색]: Neo4j 지식 그래프에서 구조적 관계를 탐색한 결과
2. [벡터 검색]: 원본 문서에서 의미적으로 유사한 청크

두 결과를 종합하여 정확하고 근거 있는 답변을 작성하세요.
- 수치/기준값은 반드시 출처(법령명 또는 문서)를 명시하세요.
- 정보가 없으면 "해당 정보를 찾을 수 없습니다"라고 답하세요."""


@dataclass
class RetrievalContext:
    graph_result: str
    vector_chunks: list[str]
    cypher_query: str | None = None


@dataclass
class HybridAnswer:
    answer: str
    graph_result: str
    vector_chunks: list[str]
    cypher_query: str | None
    sources: list[str]


async def hybrid_query(question: str, graph: "Neo4jGraph", k_vector: int = 4) -> HybridAnswer:
    """그래프 + 벡터 검색을 병렬로 실행 후 통합 답변 생성."""
    import asyncio

    # 그래프 검색과 벡터 검색 병렬 실행
    graph_task = asyncio.create_task(_run_graph_search(question, graph))
    vector_task = asyncio.create_task(asyncio.to_thread(vector_search, question, k_vector))

    graph_result, cypher_query = await graph_task
    vector_docs = await vector_task

    vector_chunks = [doc.page_content for doc in vector_docs]
    sources = list({doc.metadata.get("source", "unknown") for doc in vector_docs})

    context = _build_context(graph_result, vector_chunks)
    answer = await _generate_answer(question, context)

    logger.info("Hybrid query complete", question=question[:60])
    return HybridAnswer(
        answer=answer,
        graph_result=graph_result,
        vector_chunks=vector_chunks,
        cypher_query=cypher_query,
        sources=sources,
    )


async def _run_graph_search(question: str, graph: "Neo4jGraph") -> tuple[str, str | None]:
    from app.services.graph_retriever import build_cypher_chain
    try:
        chain = build_cypher_chain(graph)
        result = await chain.ainvoke({"query": question})
        raw_answer = result.get("result", "")
        steps = result.get("intermediate_steps", [])
        cypher = steps[0].get("query") if steps else None
        return raw_answer, cypher
    except Exception as e:
        logger.warning("Graph search failed, falling back to vector only", error=str(e))
        return "", None


def _build_context(graph_result: str, vector_chunks: list[str]) -> str:
    parts = []
    if graph_result:
        parts.append(f"[그래프 검색]\n{graph_result}")
    if vector_chunks:
        joined = "\n---\n".join(vector_chunks[:3])  # 상위 3개만 사용
        parts.append(f"[벡터 검색]\n{joined}")
    return "\n\n".join(parts) if parts else "검색 결과 없음"


async def _generate_answer(question: str, context: str) -> str:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key,
        temperature=0.1,
        max_tokens=1024,
    )
    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=f"컨텍스트:\n{context}\n\n질문: {question}"),
    ]
    response = await llm.ainvoke(messages)
    return response.content
