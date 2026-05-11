import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.hybrid_retriever import HybridAnswer


_MOCK_ANSWER = HybridAnswer(
    answer="탁도 기준은 0.5 NTU입니다.",
    graph_result="수질기준(탁도): 0.5 NTU",
    vector_chunks=["수도법 제26조에 따르면 탁도는 0.5 NTU 이하..."],
    cypher_query="MATCH (s:수질기준 {name: '탁도'}) RETURN s",
    sources=["수도법.pdf"],
)


@pytest.mark.asyncio
async def test_query_endpoint_returns_200():
    with patch("app.api.v1.query.process_query", new_callable=AsyncMock) as mock_q:
        mock_q.return_value = _MOCK_ANSWER
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/query", json={"question": "탁도 기준은?"})

    assert response.status_code == 200
    body = response.json()
    assert "answer" in body
    assert "cypher_query" in body


@pytest.mark.asyncio
async def test_query_too_short_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/query", json={"question": "a"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_query_cache_hit():
    with patch("app.api.v1.query.process_query", new_callable=AsyncMock) as mock_q:
        mock_q.return_value = _MOCK_ANSWER
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/api/v1/query", json={"question": "캐시테스트?"})
            await client.post("/api/v1/query", json={"question": "캐시테스트?"})

    # 두 번 요청했지만 LLM은 한 번만 호출
    assert mock_q.call_count == 1
