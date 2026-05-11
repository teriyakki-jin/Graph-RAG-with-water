import type { GraphData, QueryResponse, SSEContext } from "@/types/graph";

const BASE = "/api/v1";

export async function fetchGraph(limit = 120): Promise<GraphData> {
  const res = await fetch(`${BASE}/graph/nodes?limit=${limit}`);
  if (!res.ok) throw new Error(`Graph fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchNeighbors(name: string): Promise<GraphData> {
  const res = await fetch(`${BASE}/graph/neighbors?name=${encodeURIComponent(name)}`);
  if (!res.ok) throw new Error(`Neighbors fetch failed: ${res.status}`);
  return res.json();
}

export async function querySync(question: string): Promise<QueryResponse> {
  const res = await fetch(`${BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error(`Query failed: ${res.status}`);
  return res.json();
}

export interface StreamCallbacks {
  onStatus(msg: string): void;
  onContext(ctx: SSEContext): void;
  onToken(text: string): void;
  onDone(): void;
  onError(err: Error): void;
}

export function queryStream(question: string, callbacks: StreamCallbacks): () => void {
  const url = `${BASE}/query/stream?question=${encodeURIComponent(question)}`;
  const es = new EventSource(url);

  es.addEventListener("status", (e) => {
    const d = JSON.parse(e.data);
    callbacks.onStatus(d.message);
  });
  es.addEventListener("context", (e) => {
    callbacks.onContext(JSON.parse(e.data));
  });
  es.addEventListener("token", (e) => {
    const d = JSON.parse(e.data);
    callbacks.onToken(d.text);
  });
  es.addEventListener("done", () => {
    callbacks.onDone();
    es.close();
  });
  es.onerror = () => {
    callbacks.onError(new Error("SSE 연결 오류"));
    es.close();
  };

  return () => es.close();
}
