import pytest
from unittest.mock import AsyncMock, patch

from app.services.query_service import _is_complex, _decompose_question


def test_is_complex_short_simple():
    assert _is_complex("탁도 기준은?") is False


def test_is_complex_keyword():
    assert _is_complex("응집과 침전의 차이는?") is True


def test_is_complex_long_question():
    long_q = "수처리 공정에서 각 단계별로 사용되는 약품의 종류와 그 역할에 대해 설명해주세요"
    assert _is_complex(long_q) is True


@pytest.mark.asyncio
async def test_decompose_returns_list():
    mock_response = AsyncMock()
    mock_response.content = "1. 응집 공정이란?\n2. 침전 공정이란?\n3. 두 공정의 차이는?"

    with patch("langchain_openai.ChatOpenAI") as MockLLM:
        instance = MockLLM.return_value
        instance.ainvoke = AsyncMock(return_value=mock_response)
        result = await _decompose_question("응집과 침전의 차이는?")

    assert isinstance(result, list)
    assert len(result) == 3
    assert all(isinstance(q, str) and q for q in result)
