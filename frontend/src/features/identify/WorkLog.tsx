import { useRef, useEffect } from "react";
import type { LogLine } from "./useDiscoverStream";
import { COPY } from "@/lib/copy";

export function WorkLog({
  lines,
  follow,
  onFollowChange,
  newCount,
  onClearNew,
  onLineClick,
}: {
  lines: LogLine[];
  follow: boolean;
  onFollowChange: (v: boolean) => void;
  newCount: number;
  onClearNew: () => void;
  onLineClick?: (line: LogLine) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (follow && el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [lines.length, follow]);

  const onScroll = () => {
    const el = ref.current;
    if (!el) return;
    const fromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    if (fromBottom > 40) onFollowChange(false);
  };

  return (
    <div className="flex flex-col h-full border border-border rounded bg-surface min-h-0">
      <div className="px-3 py-2 border-b border-border flex items-center justify-between">
        <span className="font-mono text-[11px] uppercase text-ink-faint">Ops log</span>
        {!follow && newCount > 0 ? (
          <button
            type="button"
            className="text-[11px] font-mono text-sage-600"
            onClick={() => {
              onFollowChange(true);
              onClearNew();
            }}
          >
            {COPY.logPill(newCount)}
          </button>
        ) : null}
      </div>
      <div ref={ref} onScroll={onScroll} className="flex-1 overflow-y-auto divide-y divide-border">
        {lines.map((line) => (
          <button
            key={line.id}
            type="button"
            className="w-full text-left px-3 py-2 hover:bg-surface-sunken transition-colors duration-100"
            onClick={() => onLineClick?.(line)}
          >
            <div className="flex items-center gap-2 mb-0.5">
              <span className="font-mono text-[10px] px-1 py-0.5 rounded-sm bg-surface-sunken text-ink-faint">
                {line.verb}
              </span>
              <span className="font-mono text-[10px] text-ink-faint font-tabular">{line.t}ms</span>
            </div>
            <p className="text-[12px] text-ink">{line.body}</p>
          </button>
        ))}
        {lines.length === 0 ? (
          <p className="px-3 py-4 text-[12px] text-ink-faint">Awaiting discovery…</p>
        ) : null}
      </div>
    </div>
  );
}

export function SourceList({ sources }: { sources: string[] }) {
  return (
    <div className="flex flex-col h-full border border-border rounded bg-surface min-h-0">
      <div className="px-3 py-2 border-b border-border font-mono text-[11px] uppercase text-ink-faint">
        Sources ({sources.length})
      </div>
      <ul className="flex-1 overflow-y-auto divide-y divide-border">
        {sources.map((url) => (
          <li key={url} className="px-3 py-2 text-[12px] font-mono text-ink truncate">
            {url}
          </li>
        ))}
        {sources.length === 0 ? (
          <li className="px-3 py-4 text-[12px] text-ink-faint">Collecting…</li>
        ) : null}
      </ul>
    </div>
  );
}
