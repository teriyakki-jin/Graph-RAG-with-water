"use client";
import { useEffect, useState, useCallback } from "react";
import { Database, RefreshCw } from "lucide-react";
import GraphViewer from "@/components/GraphViewer";
import QueryPanel from "@/components/QueryPanel";
import NodeDetail from "@/components/NodeDetail";
import { fetchGraph, fetchNeighbors } from "@/lib/api";
import type { GraphData, GraphNode, SSEContext } from "@/types/graph";

export default function Home() {
  const [graph, setGraph] = useState<GraphData>({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [highlightIds, setHighlightIds] = useState<Set<string>>(new Set());

  const loadGraph = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchGraph(120);
      setGraph(data);
    } catch {
      // Neo4j 미연결 상태에서도 UI는 표시
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadGraph(); }, [loadGraph]);

  const handleNodeClick = useCallback((node: GraphNode) => {
    setSelectedNode(node);
  }, []);

  const handleExpand = useCallback(async (node: GraphNode) => {
    try {
      const neighbors = await fetchNeighbors(node.label);
      // 기존 그래프에 이웃 노드 병합 (중복 제거)
      setGraph((prev) => {
        const existingIds = new Set(prev.nodes.map((n) => n.id));
        const newNodes = neighbors.nodes.filter((n) => !existingIds.has(n.id));
        const existingEdgeKeys = new Set(
          prev.edges.map((e) => `${typeof e.source === "string" ? e.source : e.source.id}-${typeof e.target === "string" ? e.target : e.target.id}`)
        );
        const newEdges = neighbors.edges.filter((e) => {
          const key = `${typeof e.source === "string" ? e.source : e.source.id}-${typeof e.target === "string" ? e.target : e.target.id}`;
          return !existingEdgeKeys.has(key);
        });
        return { nodes: [...prev.nodes, ...newNodes], edges: [...prev.edges, ...newEdges] };
      });
      // 이웃 노드 하이라이트
      setHighlightIds(new Set(neighbors.nodes.map((n) => n.id)));
    } catch {
      // 이웃 노드 조회 실패 시 현재 그래프 상태 유지
    }
  }, []);

  // Cypher 쿼리에서 인용 문자열을 추출해 노드 label과 정확히 대조한다.
  // 단순 substring 매칭은 짧은 노드명이 다른 단어에 잘못 포함되는 오탐을 낳는다.
  const extractCypherEntities = useCallback((cypher: string): Set<string> => {
    const entities = new Set<string>();
    const regex = /['"]([^'"]+)['"]/g;
    let m: RegExpExecArray | null;
    while ((m = regex.exec(cypher)) !== null) {
      entities.add(m[1]);
    }
    return entities;
  }, []);

  const handleContext = useCallback((ctx: SSEContext) => {
    if (!ctx.cypher_query) return;
    const entities = extractCypherEntities(ctx.cypher_query);
    const mentioned = graph.nodes
      .filter((n) => entities.has(n.label))
      .map((n) => n.id);
    if (mentioned.length > 0) setHighlightIds(new Set(mentioned));
  }, [graph.nodes, extractCypherEntities]);

  return (
    <div className="flex flex-col h-screen bg-surface text-gray-100">
      {/* 헤더 */}
      <header className="flex items-center justify-between px-5 py-3 border-b border-border shrink-0">
        <div className="flex items-center gap-2">
          <Database size={20} className="text-blue-400" />
          <span className="font-semibold text-base">Graph RAG</span>
          <span className="text-xs text-gray-500 ml-1">수처리 지식 그래프</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-500">
            노드 {graph.nodes.length} · 관계 {graph.edges.length}
          </span>
          <button
            onClick={loadGraph}
            className="p-1.5 rounded-lg hover:bg-panel transition-colors text-gray-400 hover:text-gray-200"
            title="그래프 새로고침"
          >
            <RefreshCw size={15} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </header>

      {/* 메인 레이아웃: 그래프(좌) + 패널(우) */}
      <div className="flex flex-1 min-h-0 gap-0">
        {/* 그래프 영역 */}
        <div className="flex-1 relative min-w-0">
          <GraphViewer
            nodes={graph.nodes}
            edges={graph.edges}
            highlightIds={highlightIds}
            onNodeClick={handleNodeClick}
          />
          {/* 선택 노드 상세 */}
          {selectedNode && (
            <div className="absolute top-3 left-3 w-64 z-10">
              <NodeDetail
                node={selectedNode}
                onClose={() => setSelectedNode(null)}
                onExpand={handleExpand}
              />
            </div>
          )}
        </div>

        {/* 질의 패널 */}
        <div className="w-[380px] shrink-0 border-l border-border bg-panel p-4 flex flex-col min-h-0">
          <h2 className="text-sm font-medium text-gray-300 mb-3">질의 응답</h2>
          <div className="flex-1 min-h-0">
            <QueryPanel onContext={handleContext} />
          </div>
        </div>
      </div>
    </div>
  );
}
