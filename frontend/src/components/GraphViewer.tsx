"use client";
import { useRef, useEffect, useState, useCallback } from "react";
import { useGraphSimulation } from "@/hooks/useGraphSimulation";
import { NODE_STYLES } from "@/lib/nodeColors";
import type { GraphNode, GraphEdge } from "@/types/graph";

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
  highlightIds?: Set<string>;
  onNodeClick?(node: GraphNode): void;
}

export default function GraphViewer({ nodes, edges, highlightIds = new Set(), onNodeClick }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 800, height: 600 });

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      setSize({ width, height });
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  const handleNodeClick = useCallback(
    (node: GraphNode) => onNodeClick?.(node),
    [onNodeClick]
  );

  useGraphSimulation(svgRef, nodes, edges, {
    width: size.width,
    height: size.height,
    highlightIds,
    onNodeClick: handleNodeClick,
  });

  return (
    <div ref={containerRef} className="relative w-full h-full bg-surface rounded-xl overflow-hidden">
      {nodes.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center text-gray-500 text-sm">
          그래프 데이터가 없습니다. 파이프라인을 먼저 실행해주세요.
        </div>
      )}
      <svg ref={svgRef} width={size.width} height={size.height} />

      {/* 범례 */}
      <div className="absolute bottom-3 left-3 bg-panel/90 border border-border rounded-lg p-2 flex flex-col gap-1">
        {Object.entries(NODE_STYLES)
          .filter(([k]) => k !== "Entity")
          .map(([type, style]) => (
            <div key={type} className="flex items-center gap-2 text-xs text-gray-300">
              <span
                className="inline-block rounded-full"
                style={{ width: 10, height: 10, background: style.fill, border: `1.5px solid ${style.stroke}` }}
              />
              {type}
            </div>
          ))}
      </div>
    </div>
  );
}
