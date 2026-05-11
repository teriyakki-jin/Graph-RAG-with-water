"use client";
import { useEffect, useRef } from "react";
import * as d3 from "d3";
import type { GraphNode, GraphEdge } from "@/types/graph";
import { getNodeStyle } from "@/lib/nodeColors";

interface Options {
  width: number;
  height: number;
  highlightIds: Set<string>;
  onNodeClick(node: GraphNode): void;
}

export function useGraphSimulation(
  svgRef: React.RefObject<SVGSVGElement | null>,
  nodes: GraphNode[],
  edges: GraphEdge[],
  { width, height, highlightIds, onNodeClick }: Options
) {
  const simRef = useRef<d3.Simulation<GraphNode, GraphEdge> | null>(null);

  useEffect(() => {
    if (!svgRef.current || nodes.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    // 줌/패닝
    const g = svg.append("g");
    svg.call(
      d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.2, 4])
        .on("zoom", (event) => g.attr("transform", event.transform))
    );

    // 화살표 마커
    svg.append("defs").append("marker")
      .attr("id", "arrow")
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 22)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("fill", "#4B5563");

    // 엣지
    const link = g.append("g")
      .selectAll("line")
      .data(edges)
      .join("line")
      .attr("stroke", "#2a2d3e")
      .attr("stroke-width", 1.5)
      .attr("marker-end", "url(#arrow)");

    // 엣지 레이블
    const linkLabel = g.append("g")
      .selectAll("text")
      .data(edges)
      .join("text")
      .attr("font-size", 9)
      .attr("fill", "#6B7280")
      .attr("text-anchor", "middle")
      .text((d) => d.type);

    // 노드 그룹 — selectAll 제네릭으로 타입 명시
    const node = g.append("g")
      .selectAll<SVGGElement, GraphNode>("g")
      .data(nodes)
      .join("g")
      .attr("cursor", "pointer")
      .on("click", (_, d) => onNodeClick(d))
      .call(
        d3.drag<SVGGElement, GraphNode>()
          .on("start", (event, d) => {
            if (!event.active) simRef.current?.alphaTarget(0.3).restart();
            d.fx = d.x; d.fy = d.y;
          })
          .on("drag", (event, d) => { d.fx = event.x; d.fy = event.y; })
          .on("end", (event, d) => {
            if (!event.active) simRef.current?.alphaTarget(0);
            d.fx = null; d.fy = null;
          })
      );

    node.append("circle")
      .attr("r", (d) => getNodeStyle(d.type).r)
      .attr("fill", (d) => getNodeStyle(d.type).fill)
      .attr("stroke", (d) =>
        highlightIds.has(d.id) ? "#FBBF24" : getNodeStyle(d.type).stroke
      )
      .attr("stroke-width", (d) => highlightIds.has(d.id) ? 3 : 1.5);

    node.append("text")
      .attr("dy", (d) => getNodeStyle(d.type).r + 12)
      .attr("text-anchor", "middle")
      .attr("font-size", 10)
      .attr("fill", "#D1D5DB")
      .text((d) => d.label.length > 12 ? d.label.slice(0, 12) + "…" : d.label);

    // 툴팁
    node.append("title").text((d) =>
      `${d.type}: ${d.label}\n${JSON.stringify(d.properties, null, 2)}`
    );

    // 시뮬레이션
    simRef.current = d3.forceSimulation<GraphNode>(nodes)
      .force("link", d3.forceLink<GraphNode, GraphEdge>(edges)
        .id((d) => d.id).distance(100))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide(30))
      .on("tick", () => {
        link
          .attr("x1", (d) => (d.source as GraphNode).x ?? 0)
          .attr("y1", (d) => (d.source as GraphNode).y ?? 0)
          .attr("x2", (d) => (d.target as GraphNode).x ?? 0)
          .attr("y2", (d) => (d.target as GraphNode).y ?? 0);

        linkLabel
          .attr("x", (d) => (((d.source as GraphNode).x ?? 0) + ((d.target as GraphNode).x ?? 0)) / 2)
          .attr("y", (d) => (((d.source as GraphNode).y ?? 0) + ((d.target as GraphNode).y ?? 0)) / 2);

        node.attr("transform", (d) => `translate(${d.x ?? 0},${d.y ?? 0})`);
      });

    return () => { simRef.current?.stop(); };
  }, [nodes, edges, width, height, highlightIds, onNodeClick, svgRef]);
}
