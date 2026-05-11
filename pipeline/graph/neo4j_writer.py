from langchain_experimental.graph_transformers.llm import GraphDocument
from langchain_neo4j import Neo4jGraph
from langchain_neo4j.vectorstores.neo4j_vector import Neo4jVector
from langchain_community.embeddings import HuggingFaceEmbeddings

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def get_neo4j_graph() -> Neo4jGraph:
    return Neo4jGraph(
        url=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password,
        enhanced_schema=True,
    )


def get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=settings.embedding_model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def write_graph_documents(
    graph_docs: list[GraphDocument],
    graph: Neo4jGraph,
    include_source: bool = True,
) -> None:
    """GraphDocument를 Neo4j에 적재. MERGE로 중복 노드 방지."""
    if not graph_docs:
        logger.warning("No graph documents to write")
        return

    graph.add_graph_documents(
        graph_docs,
        baseEntityLabel=True,  # __Entity__ 라벨로 통합 인덱스 생성
        include_source=include_source,  # 원본 청크 Document 노드도 저장
    )
    total_nodes = sum(len(g.nodes) for g in graph_docs)
    total_rels = sum(len(g.relationships) for g in graph_docs)
    logger.info("Graph written", nodes=total_nodes, relationships=total_rels)


def build_vector_index(graph: Neo4jGraph) -> Neo4jVector:
    """청크 Document 노드에 벡터 인덱스 구축."""
    embeddings = get_embeddings()
    vector_store = Neo4jVector.from_existing_graph(
        embedding=embeddings,
        url=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password,
        index_name="document_chunks",
        node_label="Document",          # include_source=True 로 생성된 노드
        text_node_properties=["text"],
        embedding_node_property="embedding",
    )
    logger.info("Vector index built", index="document_chunks")
    return vector_store


def ensure_constraints(graph: Neo4jGraph) -> None:
    """중복 방지를 위한 유니크 제약 조건 생성."""
    constraints = [
        "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (n:__Entity__) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT document_id IF NOT EXISTS FOR (n:Document) REQUIRE n.id IS UNIQUE",
    ]
    for cypher in constraints:
        try:
            graph.query(cypher)
        except Exception as e:
            logger.warning("Constraint creation skipped", error=str(e))
    logger.info("Constraints ensured")
