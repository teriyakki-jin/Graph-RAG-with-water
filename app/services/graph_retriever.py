from langchain_neo4j import Neo4jGraph
from langchain_neo4j.chains.graph_qa.cypher import GraphCypherQAChain
from langchain_openai import ChatOpenAI
from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Few-shot 예시: 수처리 도메인 Cypher ──────────────────────────────────
_FEW_SHOT_EXAMPLES = [
    {
        "question": "수돗물의 탁도 기준은?",
        "query": (
            "MATCH (s:수질기준 {id: '탁도'})-[:규정한다]-(l:법령) "
            "RETURN s.id AS 기준항목, l.id AS 법령명"
        ),
    },
    {
        "question": "정수장에서 사용하는 소독 공정은?",
        "query": (
            "MATCH (f:설비)-[:처리한다]->(p:공정)-[:사용한다]->(m:물질) "
            "WHERE f.id CONTAINS '정수장' AND p.id CONTAINS '소독' "
            "RETURN p.id AS 공정, collect(m.id) AS 사용물질"
        ),
    },
    {
        "question": "K-water가 관할하는 지역은?",
        "query": (
            "MATCH (o:기관 {id: 'K-water'})-[:관할한다]->(r:지역) "
            "RETURN collect(r.id) AS 관할지역"
        ),
    },
    {
        "question": "수도법에서 규정하는 수질기준 목록은?",
        "query": (
            "MATCH (l:법령 {id: '수도법'})-[:규정한다]->(s:수질기준) "
            "RETURN s.id AS 항목 ORDER BY s.id"
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
        "- 노드 타입: 법령, 조문, 수질기준, 측정값, 설비, 공정, 물질, 기관, 지역, 사고\n"
        "- 노드 식별자 속성은 반드시 n.id 를 사용 (n.name 은 존재하지 않음)\n"
        "- LIMIT 10을 기본으로 사용\n"
        "- 존재하지 않는 속성은 조회하지 않음\n"
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
