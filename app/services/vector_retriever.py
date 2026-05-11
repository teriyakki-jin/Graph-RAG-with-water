from langchain_neo4j.vectorstores.neo4j_vector import Neo4jVector
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_vector_store: Neo4jVector | None = None


def get_vector_store() -> Neo4jVector:
    global _vector_store
    if _vector_store is None:
        embeddings = HuggingFaceEmbeddings(
            model_name=settings.embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        _vector_store = Neo4jVector(
            embedding=embeddings,
            url=settings.neo4j_uri,
            username=settings.neo4j_username,
            password=settings.neo4j_password,
            index_name="document_chunks",
            node_label="Document",
            text_node_property="text",
            embedding_node_property="embedding",
        )
        logger.info("Vector store initialized")
    return _vector_store


def vector_search(question: str, k: int = 4) -> list[Document]:
    """질문과 유사한 청크 k개 반환."""
    try:
        store = get_vector_store()
        results = store.similarity_search(question, k=k)
        logger.info("Vector search done", question=question[:50], hits=len(results))
        return results
    except Exception as e:
        logger.error("Vector search failed", error=str(e))
        return []
