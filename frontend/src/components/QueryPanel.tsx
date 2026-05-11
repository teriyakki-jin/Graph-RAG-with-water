"use client";
import { useState, useRef, useCallback } from "react";
import { Send, Loader2, ChevronDown, ChevronUp, Code2 } from "lucide-react";
import { queryStream } from "@/lib/api";
import type { SSEContext } from "@/types/graph";
import clsx from "clsx";

interface Props {
  onContext?(ctx: SSEContext): void;
}

export default function QueryPanel({ onContext }: Props) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [status, setStatus] = useState("");
  const [context, setContext] = useState<SSEContext | null>(null);
  const [loading, setLoading] = useState(false);
  const [showCypher, setShowCypher] = useState(false);
  const stopRef = useRef<(() => void) | null>(null);

  const submit = useCallback(() => {
    if (!question.trim() || loading) return;
    setAnswer("");
    setContext(null);
    setStatus("");
    setLoading(true);

    stopRef.current = queryStream(question, {
      onStatus: setStatus,
      onContext: (ctx) => {
        setContext(ctx);
        onContext?.(ctx);
      },
      onToken: (text) => setAnswer((prev) => prev + text),
      onDone: () => { setLoading(false); setStatus(""); },
      onError: (err) => { setStatus(`오류: ${err.message}`); setLoading(false); },
    });
  }, [question, loading, onContext]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); }
  };

  return (
    <div className="flex flex-col h-full gap-3">
      {/* 입력 */}
      <div className="flex gap-2 items-end">
        <textarea
          className="flex-1 bg-panel border border-border rounded-lg px-3 py-2 text-sm text-gray-100
                     placeholder-gray-500 resize-none focus:outline-none focus:border-blue-500 min-h-[60px]"
          placeholder="수처리 도메인 질문을 입력하세요 (Shift+Enter: 줄바꿈)"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
          rows={2}
        />
        <button
          onClick={submit}
          disabled={!question.trim() || loading}
          className="p-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40
                     disabled:cursor-not-allowed transition-colors"
        >
          {loading
            ? <Loader2 size={18} className="animate-spin text-white" />
            : <Send size={18} className="text-white" />}
        </button>
      </div>

      {/* 상태 메시지 */}
      {status && (
        <p className="text-xs text-blue-400 animate-pulse">{status}</p>
      )}

      {/* 답변 */}
      {answer && (
        <div className="flex-1 overflow-y-auto bg-panel border border-border rounded-lg p-3">
          <p className="text-sm text-gray-100 whitespace-pre-wrap leading-relaxed">{answer}</p>
        </div>
      )}

      {/* 메타 정보 (소스, Cypher) */}
      {context && (
        <div className="flex flex-col gap-2 text-xs">
          {context.sources.length > 0 && (
            <div className="flex gap-1 flex-wrap">
              <span className="text-gray-500">출처:</span>
              {context.sources.map((s) => (
                <span key={s} className="bg-panel border border-border px-2 py-0.5 rounded text-gray-300">
                  {s.split(/[\\/]/).pop()}
                </span>
              ))}
            </div>
          )}

          {context.cypher_query && (
            <div>
              <button
                onClick={() => setShowCypher((v) => !v)}
                className="flex items-center gap-1 text-gray-400 hover:text-gray-200 transition-colors"
              >
                <Code2 size={13} />
                Cypher 쿼리 보기
                {showCypher ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
              </button>
              {showCypher && (
                <pre className={clsx(
                  "mt-1 p-2 rounded bg-surface border border-border text-green-400",
                  "overflow-x-auto text-[11px] leading-relaxed"
                )}>
                  {context.cypher_query}
                </pre>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
