from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_experimental.graph_transformers.llm import GraphDocument

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── 수처리 도메인 온톨로지 ──────────────────────────────────────────────────
ALLOWED_NODES = [
    # ── 법제 ──────────────────────────────────────
    "법령",             # 수도법, 먹는물관리법
    "조문",             # 제N조
    "고시",             # 환경부 고시

    # ── 수질기준 (세분화) ─────────────────────────
    "건강항목",         # 건강상 유해영향 무기물질/유기물질/소독부산물
    "심미적항목",       # 탁도, 색도, 냄새, 맛, 경도 등
    "소독부산물",       # THM, 할로아세틱산 등
    "미생물항목",       # 일반세균, 대장균, 분원성 대장균군

    # ── 수치 정보 ─────────────────────────────────
    "수질기준값",       # 기준값 + 단위 (예: 0.5 NTU)
    "검사주기",         # 매일/매주/매월
    "검사방법",         # 측정 분석 방법

    # ── 시설·공정 ─────────────────────────────────
    "정수장",           # 개별 정수장
    "공정",             # 응집, 침전, 여과, 소독
    "소독방법",         # 염소, 오존, UV
    "약품",             # 황산알루미늄, PAC, 차아염소산나트륨

    # ── 기관·지역 ─────────────────────────────────
    "기관",             # K-water, 환경부, 지자체
    "지역",             # 광역/지방상수도 구역

    # ── 사고·위반 ─────────────────────────────────
    "수질사고",         # 사고 사례
    "위반항목",         # 기준 초과 항목
    "처벌규정",         # 벌칙 조항
]

ALLOWED_RELATIONSHIPS = [
    # 법제 관계
    "규정한다",         # 법령/조문 → 수질기준값/건강항목/미생물항목
    "포함한다",         # 법령 → 조문, 건강항목 → 소독부산물
    "준용한다",         # 고시 → 조문
    "개정한다",         # 법령 → 법령

    # 기준 관계
    "기준값이다",       # 건강항목/심미적항목 → 수질기준값
    "검사주기이다",     # 항목 → 검사주기
    "검사방법이다",     # 항목 → 검사방법

    # 시설·공정 관계
    "처리한다",         # 정수장/공정 → 다음 공정
    "사용한다",         # 공정/소독방법 → 약품
    "적용한다",         # 정수장 → 소독방법

    # 기관·책임 관계
    "관할한다",         # 기관 → 지역/정수장
    "감독한다",         # 기관 → 기관
    "운영한다",         # 기관 → 정수장

    # 사고·위반 관계
    "위반한다",         # 수질사고 → 건강항목/심미적항목
    "초과한다",         # 수질사고 → 수질기준값
    "처벌받는다",       # 기관 → 처벌규정
    "원인이다",         # 수질사고 → 위반항목
]


def build_graph_transformer() -> LLMGraphTransformer:
    llm = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key,
        temperature=0,
        max_tokens=4096,
    )
    return LLMGraphTransformer(
        llm=llm,
        allowed_nodes=ALLOWED_NODES,
        allowed_relationships=ALLOWED_RELATIONSHIPS,
        # 노드에 추가 속성도 추출 (수치, 단위 등)
        node_properties=["설명", "수치", "단위", "조문번호"],
        relationship_properties=["조건", "예외"],
        strict_mode=False,  # 온톨로지 외 관계도 연관된다로 수용
    )


async def extract_graph_documents(
    chunks: list[Document],
    transformer: LLMGraphTransformer,
    batch_size: int = 5,
) -> list[GraphDocument]:
    """청크를 배치로 처리하여 GraphDocument 목록 반환."""
    graph_docs: list[GraphDocument] = []

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        logger.info(
            "Extracting graph",
            batch=f"{i // batch_size + 1}/{(len(chunks) - 1) // batch_size + 1}",
            chunks=len(batch),
        )
        try:
            result = await transformer.aconvert_to_graph_documents(batch)
            graph_docs.extend(result)
            logger.info(
                "Batch extracted",
                nodes=sum(len(g.nodes) for g in result),
                relationships=sum(len(g.relationships) for g in result),
            )
        except Exception as e:
            logger.error("Batch extraction failed", batch_start=i, error=str(e))

    return graph_docs
