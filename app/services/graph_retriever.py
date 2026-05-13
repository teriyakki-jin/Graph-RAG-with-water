from langchain_neo4j import Neo4jGraph
from langchain_neo4j.chains.graph_qa.cypher import GraphCypherQAChain
from langchain_openai import ChatOpenAI
from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Few-shot 예시: 수처리 도메인 Cypher ──────────────────────────────────
# 모든 노드는 :__Entity__ 공통 레이블을 가짐 (LangChain LLMGraphTransformer 규약)
# 도메인 레이블(법령, 심미적항목 등)은 추가 레이블로 존재하지만 추출 품질에 따라 다를 수 있으므로
# 폴백으로 :__Entity__ + n.id CONTAINS 패턴을 사용해 쿼리 신뢰성을 높인다.
_FEW_SHOT_EXAMPLES = [
    {
        "question": "수돗물의 탁도 기준은?",
        "query": (
            "MATCH (s:__Entity__)-[r]->(v:__Entity__) "
            "WHERE s.id CONTAINS '탁도' "
            "AND (type(r) IN ['기준값이다', '규정한다', '포함한다']) "
            "RETURN s.id AS 항목, type(r) AS 관계, v.id AS 값 LIMIT 10"
        ),
    },
    {
        "question": "정수장에서 사용하는 소독 공정은?",
        "query": (
            "MATCH (p:__Entity__)-[:사용한다]->(m:__Entity__) "
            "WHERE p.id CONTAINS '소독' "
            "RETURN p.id AS 공정, collect(m.id) AS 사용물질 LIMIT 10"
        ),
    },
    {
        "question": "K-water가 관할하는 지역은?",
        "query": (
            "MATCH (o:__Entity__)-[:관할한다]->(r:__Entity__) "
            "WHERE o.id CONTAINS 'K-water' OR o.id CONTAINS 'K water' "
            "RETURN o.id AS 기관, collect(r.id) AS 관할지역 LIMIT 20"
        ),
    },
    {
        "question": "수도법에서 규정하는 수질기준 항목은?",
        "query": (
            "MATCH (l:__Entity__)-[:규정한다]->(s:__Entity__) "
            "WHERE l.id CONTAINS '수도법' "
            "RETURN s.id AS 항목 ORDER BY s.id LIMIT 20"
        ),
    },
    {
        "question": "오존 소독이 소독부산물 생성에 미치는 영향은?",
        "query": (
            "MATCH (m:__Entity__)-[r1]->(effect:__Entity__) "
            "WHERE m.id CONTAINS '오존' "
            "AND (type(r1) IN ['생성한다', '원인이다', '처리한다', '사용한다']) "
            "OPTIONAL MATCH (effect)-[r2]->(detail:__Entity__) "
            "RETURN m.id AS 소독방법, type(r1) AS 관계, effect.id AS 영향, "
            "collect(detail.id) AS 세부정보 LIMIT 15"
        ),
    },
    {
        "question": "페놀의 수질기준값과 낙동강 검출농도를 비교하면?",
        "query": (
            "MATCH (n:__Entity__)-[r]->(v:__Entity__) "
            "WHERE n.id CONTAINS '페놀' OR n.id CONTAINS '낙동강' "
            "RETURN n.id AS 항목, type(r) AS 관계, v.id AS 값 LIMIT 20"
        ),
    },
]

_EXAMPLE_TEMPLATE = PromptTemplate(
    input_variables=["question", "query"],
    template="질문: {question}\nCypher: {query}",
)

CYPHER_GENERATION_PROMPT = FewShotPromptTemplate(
    examples=_FEW_SHOT_EXAMPLES,
    example_prompt=_EXAMPLE_TEMPLATE,
    prefix=(
        "당신은 Neo4j Cypher 전문가입니다. "
        "수처리 도메인 지식 그래프에서 정보를 추출하는 Cypher 쿼리를 작성하세요.\n\n"
        "그래프 스키마:\n{schema}\n\n"
        "규칙:\n"
        "- 모든 노드는 :__Entity__ 공통 레이블을 가짐\n"
        "- 도메인 노드 타입: 법령, 조문, 건강항목, 심미적항목, 소독부산물, 미생물항목, "
        "수질기준값, 검사주기, 검사방법, 정수장, 공정, 소독방법, 약품, 기관, 지역, 수질사고, 처벌규정\n"
        "- 주요 관계 타입: 규정한다, 포함한다, 기준값이다, 처리한다, 사용한다, 적용한다, "
        "관할한다, 운영한다, 위반한다, 원인이다, 처벌받는다\n"
        "- 노드 식별자는 반드시 n.id 사용, 정확한 값 모를 때 CONTAINS 활용\n"
        "- LIMIT 10을 기본으로 사용\n"
        "- 비교·연결 질문은 OPTIONAL MATCH로 두 경로를 함께 조회하세요\n"
        "- 아래 예시를 참고하세요:\n"
    ),
    suffix="질문: {question}\nCypher:",
    input_variables=["schema", "question"],
)

QA_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template=(
        "당신은 수처리 분야 전문가입니다. "
        "아래 그래프 데이터를 바탕으로 질문에 정확하게 답하세요.\n\n"
        "그래프 조회 결과:\n{context}\n\n"
        "질문: {question}\n\n"
        "답변 (근거를 포함하여 간결하게):"
    ),
)


def build_cypher_chain(graph: Neo4jGraph) -> GraphCypherQAChain:
    llm = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key,
        temperature=0,
        max_tokens=2048,
    )
    return GraphCypherQAChain.from_llm(
        llm=llm,
        graph=graph,
        cypher_prompt=CYPHER_GENERATION_PROMPT,
        qa_prompt=QA_PROMPT,
        verbose=not settings.is_production,
        return_intermediate_steps=True,  # Cypher 쿼리 & 원시 결과 반환
        allow_dangerous_requests=True,
    )
