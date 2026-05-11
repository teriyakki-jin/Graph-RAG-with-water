from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=500)
    k_vector: int = Field(default=4, ge=1, le=20)


class QueryResponse(BaseModel):
    answer: str
    cypher_query: str | None
    graph_result: str
    sources: list[str]
    vector_chunks: list[str]


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    properties: dict


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str
    properties: dict


class GraphData(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
