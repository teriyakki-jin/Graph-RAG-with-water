import json
import asyncio
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_neo4j import Neo4jGraph

from app.core.cache import query_cache
from app.core.config import settings
from app.core.logging import get_logger
from app.models.query import QueryRequest, QueryResponse
from app.services.query_service import process_query

logger = get_logger(__name__)
router = APIRouter(prefix="/query", tags=["query"])


def _get_graph() -> Neo4jGraph:
    return Neo4jGraph(
        url=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password,
    )


@router.post("", response_model=QueryResponse)
async def query(body: QueryRequest) -> QueryResponse:
    """동기 질의 응답. 캐시 히트 시 LLM 호출 없음."""
    cache_key = f"{body.question}|k={body.k_vector}"
    cached = query_cache.get(cache_key)
    if cached:
        logger.info("Cache hit", question=body.question[:50])
        return cached

    graph = _get_graph()
    result = await process_query(body.question, graph)

    response = QueryResponse(
        answer=result.answer,
        cypher_query=result.cypher_query,
        graph_result=result.graph_result,
        sources=result.sources,
        vector_chunks=result.vector_chunks,
    )
    query_cache.set(cache_key, response)
    return response


@router.get("/stream")
async def query_stream(question: str, k_vector: int = 4) -> StreamingResponse:
    """SSE 스트리밍 응답. 답변을 토큰 단위로 전송."""
    if not question or len(question) < 2:
        raise HTTPException(status_code=422, detail="question은 2자 이상이어야 합니다.")

    return StreamingResponse(
        _stream_answer(question, k_vector),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Nginx 버퍼링 비활성화
        },
    )


async def _stream_answer(question: str, k_vector: int) -> AsyncIterator[str]:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage
    from app.services.hybrid_retriever import hybrid_query, _SYSTEM_PROMPT

    # 1. 그래프+벡터 검색 (비스트리밍)
    yield _sse("status", {"message": "검색 중..."})
    await asyncio.sleep(0)

    graph = _get_graph()
    result = await hybrid_query(question, graph, k_vector=k_vector)

    yield _sse("context", {
        "cypher_query": result.cypher_query,
        "sources": result.sources,
    })

    # 2. LLM 스트리밍
    yield _sse("status", {"message": "답변 생성 중..."})
    context = f"[그래프]\n{result.graph_result}\n\n[벡터]\n{chr(10).join(result.vector_chunks[:3])}"

    llm = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key,
        temperature=0.1,
        max_tokens=1024,
        streaming=True,
    )
    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=f"컨텍스트:\n{context}\n\n질문: {question}"),
    ]

    async for chunk in llm.astream(messages):
        if chunk.content:
            yield _sse("token", {"text": chunk.content})

    yield _sse("done", {"message": "완료"})


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
