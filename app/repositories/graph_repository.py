from app.core.database import get_session
from app.core.logging import get_logger
from app.models.query import GraphNode, GraphEdge, GraphData

logger = get_logger(__name__)

_NODE_QUERY = """
MATCH (n:__Entity__)
WHERE n.id IS NOT NULL
RETURN
  n.id           AS id,
  n.id           AS label,
  labels(n)      AS types,
  properties(n)  AS props
LIMIT $limit
"""

# $ids — 노드 쿼리로 얻은 id 목록. 양 끝점이 모두 해당 집합에 속한 엣지만 반환해
# D3.js에서 "node not found" 오류를 방지한다.
_EDGE_QUERY = """
MATCH (a:__Entity__)-[r]->(b:__Entity__)
WHERE a.id IN $ids AND b.id IN $ids
RETURN
  a.id          AS source,
  b.id          AS target,
  type(r)       AS rel_type,
  properties(r) AS props
"""

_NEIGHBOR_QUERY = """
MATCH (n:__Entity__ {id: $name})-[r]-(m:__Entity__)
WHERE m.id IS NOT NULL
RETURN
  n.id AS src_id,   n.id AS src_label,  labels(n) AS src_types,
  m.id AS tgt_id,   m.id AS tgt_label,  labels(m) AS tgt_types,
  type(r)       AS rel_type, properties(r) AS rel_props
LIMIT $limit
"""


async def fetch_graph(limit: int = 100) -> GraphData:
    async with get_session() as session:
        node_result = await session.run(_NODE_QUERY, {"limit": limit})
        nodes = [
            GraphNode(
                id=rec["id"],
                label=rec["label"] or rec["id"],
                type=next((t for t in rec["types"] if t != "__Entity__"), "Entity"),
                properties={k: v for k, v in rec["props"].items() if k != "embedding"},
            )
            async for rec in node_result
        ]

        node_ids = [n.id for n in nodes]
        edge_result = await session.run(_EDGE_QUERY, {"ids": node_ids})
        edges = [
            GraphEdge(
                source=rec["source"],
                target=rec["target"],
                type=rec["rel_type"],
                properties=rec["props"],
            )
            async for rec in edge_result
        ]

    logger.info("Graph fetched", nodes=len(nodes), edges=len(edges))
    return GraphData(nodes=nodes, edges=edges)


async def fetch_neighbors(node_name: str, limit: int = 50) -> GraphData:
    async with get_session() as session:
        result = await session.run(_NEIGHBOR_QUERY, {"name": node_name, "limit": limit})
        records = [rec async for rec in result]

    node_map: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []

    for rec in records:
        for nid, nlabel, ntypes in [
            (rec["src_id"], rec["src_label"], rec["src_types"]),
            (rec["tgt_id"], rec["tgt_label"], rec["tgt_types"]),
        ]:
            if nid not in node_map:
                node_map[nid] = GraphNode(
                    id=nid,
                    label=nlabel or nid,
                    type=next((t for t in ntypes if t != "__Entity__"), "Entity"),
                    properties={},
                )
        edges.append(GraphEdge(
            source=rec["src_id"],
            target=rec["tgt_id"],
            type=rec["rel_type"],
            properties=rec["rel_props"],
        ))

    return GraphData(nodes=list(node_map.values()), edges=edges)
