export interface GraphNode {
  id: string;
  label: string;
  type: string;
  properties: Record<string, unknown>;
  // D3 시뮬레이션이 주입하는 필드
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
}

export interface GraphEdge {
  source: string | GraphNode;
  target: string | GraphNode;
  type: string;
  properties: Record<string, unknown>;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface QueryResponse {
  answer: string;
  cypher_query: string | null;
  graph_result: string;
  sources: string[];
  vector_chunks: string[];
}

export interface SSEContext {
  cypher_query: string | null;
  sources: string[];
}
