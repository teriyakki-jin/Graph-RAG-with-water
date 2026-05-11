from fastapi import APIRouter, Query

from app.core.logging import get_logger
from app.models.query import GraphData
from app.repositories.graph_repository import fetch_graph, fetch_neighbors

logger = get_logger(__name__)
router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/nodes", response_model=GraphData)
async def get_graph_nodes(limit: int = Query(default=300, ge=1, le=500)) -> GraphData:
    """전체 지식 그래프 노드/엣지 반환. D3.js force-directed graph 연동용."""
    return await fetch_graph(limit=limit)


@router.get("/neighbors", response_model=GraphData)
async def get_neighbors(
    name: str = Query(..., description="탐색 시작 노드 이름"),
    limit: int = Query(default=50, ge=1, le=200),
) -> GraphData:
    """특정 노드의 이웃 노드/관계 반환. 질의 결과 하이라이트 연동용."""
    return await fetch_neighbors(node_name=name, limit=limit)
