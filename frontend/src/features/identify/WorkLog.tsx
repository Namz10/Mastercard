import { useRef, useEffect } from "react";
import type { LogLine } from "./useDiscoverStream";
import { COPY } from "@/lib/copy";

/** Structure from 21st Audit Log id:25163 — timestamp · type · body · row→drawer. No actor, no 2m-ago. */
export function WorkLog({
  lines,
  follow,
  onFollowChange,
  newCount,
  onClearNew,
  onLineClick,
  running = false,
}: {
  lines: LogLine[];
  follow: boolean;
  onFollowChange: (v: boolean) => void;
  newCount: number;
  onClearNew: () => void;
  onLineClick?: (line: LogLine) => void;
  running?: boolean;
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
    <div className="panel flex flex-col h-full min-h-0">
      <div className="h-9 px-3 border-b border-border flex items-center justify-between shrink-0">
        <span className="font-mono text-[11px] uppercase text-ink-faint">Ops log</span>
        {!follow && newCount > 0 ? (
          <button
            type="button"
            className="text-[11px] font-mono text-accent"
            onClick={() => {
              onFollowChange(true);
              onClearNew();
            }}
          >
            {COPY.logPill(newCount)}
          </button>
        ) : null}
      </div>
      <div ref={ref} onScroll={onScroll} className="flex-1 overflow-y-auto">
        {lines.map((line, i) => (
          <button
            key={line.id}
            type="button"
            className="row-insert w-full text-left h-9 px-3 flex items-center gap-3 hover:bg-accent-muted transition-colors duration-100 border-b border-border"
            onClick={() => onLineClick?.(line)}
          >
            <span className="font-mono text-[11px] text-ink-faint font-tabular w-[88px] shrink-0">
              {line.clock ?? `${line.t}ms`}
            </span>
            <span className="font-mono text-[11px] uppercase w-[72px] shrink-0 border border-border rounded-sm px-1 text-center">
              {line.verb}
            </span>
            <span className="text-[13px] text-ink truncate flex-1">{line.body}</span>
            {running && i === lines.length - 1 ? (
              <span className="tape-live-dot shrink-0" aria-label="In progress" />
            ) : null}
            {line.status ? (
              <span className="font-mono text-[10px] text-ink-faint uppercase">{line.status}</span>
            ) : null}
          </button>
        ))}
        {lines.length === 0 ? (
          <div className="px-3 py-4 flex items-center gap-2 text-[12px] text-ink-faint">
            {running ? <span className="tape-live-dot shrink-0" aria-hidden /> : null}
            <span>{running ? "Scanning allowlisted OSINT…" : "Awaiting discovery…"}</span>
          </div>
        ) : null}
      </div>
    </div>
  );
}

export function SourceList({ sources, running = false }: { sources: string[]; running?: boolean }) {
  return (
    <div className="panel flex flex-col h-full min-h-0">
      <div className="h-9 px-3 border-b border-border font-mono text-[11px] uppercase text-ink-faint flex items-center gap-2">
        {running && sources.length === 0 ? <span className="tape-live-dot shrink-0" aria-hidden /> : null}
        Sources ({sources.length})
      </div>
      <ul className="flex-1 overflow-y-auto">
        {sources.map((url) => (
          <li
            key={url}
            className="row-insert h-9 px-3 flex items-center text-[12px] font-mono text-ink truncate border-b border-border"
          >
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
