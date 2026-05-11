"use client";
import { X } from "lucide-react";
import type { GraphNode } from "@/types/graph";
import { getNodeStyle } from "@/lib/nodeColors";

interface Props {
  node: GraphNode;
  onClose(): void;
  onExpand(node: GraphNode): void;
}

export default function NodeDetail({ node, onClose, onExpand }: Props) {
  const style = getNodeStyle(node.type);
  const props = Object.entries(node.properties).filter(([k]) => k !== "embedding");

  return (
    <div className="bg-panel border border-border rounded-xl p-4 flex flex-col gap-3 text-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span
            className="rounded-full shrink-0"
            style={{ width: 12, height: 12, background: style.fill, border: `2px solid ${style.stroke}` }}
          />
          <span className="font-medium text-gray-100 break-all">{node.label}</span>
        </div>
        <button onClick={onClose} className="text-gray-500 hover:text-gray-200 transition-colors shrink-0">
          <X size={16} />
        </button>
      </div>

      <span className="inline-block text-xs px-2 py-0.5 rounded border w-fit"
        style={{ color: style.stroke, borderColor: style.stroke }}>
        {node.type}
      </span>

      {props.length > 0 && (
        <div className="flex flex-col gap-1.5">
          {props.map(([k, v]) => (
            <div key={k} className="flex gap-2">
              <span className="text-gray-500 shrink-0">{k}:</span>
              <span className="text-gray-300 break-all">{String(v)}</span>
            </div>
          ))}
        </div>
      )}

      <button
        onClick={() => onExpand(node)}
        className="mt-1 text-xs text-blue-400 hover:text-blue-300 text-left transition-colors"
      >
        이웃 노드 탐색 →
      </button>
    </div>
  );
}
