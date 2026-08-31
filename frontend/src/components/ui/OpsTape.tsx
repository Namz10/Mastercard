import { useRef, useEffect } from "react";
import clsx from "clsx";
import { COPY } from "@/lib/copy";
import type { OpsTapeLine } from "@/lib/ops-tape-types";

export type { OpsTapeLine } from "@/lib/ops-tape-types";

function verbChipClass(status?: string) {
  if (status === "active") return "border-ink bg-sage-100/60 text-ink";
  if (status === "done") return "border-sage-600/40 text-sage-700 bg-sage-100/30";
  if (status === "pending") return "border-border text-ink-faint opacity-60";
  return "border-border text-ink";
}

export function OpsTape({
  lines,
  follow,
  onFollowChange,
  newCount,
  onClearNew,
  onLineClick,
  running = false,
  emptyLabel = "Awaiting…",
  className,
  variant = "rail",
}: {
  lines: OpsTapeLine[];
  follow?: boolean;
  onFollowChange?: (v: boolean) => void;
  newCount?: number;
  onClearNew?: () => void;
  onLineClick?: (line: OpsTapeLine) => void;
  running?: boolean;
  emptyLabel?: string;
  className?: string;
  variant?: "hero" | "rail";
}) {
  const ref = useRef<HTMLDivElement>(null);
  const autoFollow = follow ?? true;

  useEffect(() => {
    const el = ref.current;
    if (autoFollow && el) el.scrollTop = el.scrollHeight;
  }, [lines.length, autoFollow, lines.map((l) => l.body).join("|")]);

  const onScroll = () => {
    if (!onFollowChange) return;
    const el = ref.current;
    if (!el) return;
    const fromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    if (fromBottom > 40) onFollowChange(false);
  };

  const showPill = !autoFollow && (newCount ?? 0) > 0 && onFollowChange && onClearNew;

  return (
    <div
      className={clsx(
        "panel flex flex-col min-h-0",
        variant === "hero" ? "h-full" : "h-full",
        className,
      )}
      data-demo="ops-tape"
    >
      <div className="h-9 px-3 border-b border-border flex items-center justify-between shrink-0">
        <span className="font-mono text-[11px] uppercase text-ink-faint">Ops log</span>
        {showPill ? (
          <button
            type="button"
            className="text-[11px] font-mono text-accent"
            onClick={() => {
              onFollowChange(true);
              onClearNew();
            }}
          >
            {COPY.logPill(newCount!)}
          </button>
        ) : running ? (
          <span className="tape-live-dot shrink-0" aria-label="In progress" />
        ) : null}
      </div>
      <div ref={ref} onScroll={onScroll} className="flex-1 overflow-y-auto">
        {lines.map((line) => {
          const isActive = line.status === "active";
          const isDone = line.status === "done";
          const Row = onLineClick ? "button" : "div";
          return (
            <Row
              key={line.id}
              type={onLineClick ? "button" : undefined}
              className={clsx(
                "row-insert w-full text-left h-9 px-3 flex items-center gap-3 border-b border-border transition-colors duration-100",
                onLineClick && "hover:bg-accent-muted",
                isActive && "bg-sage-100/40",
              )}
              onClick={onLineClick ? () => onLineClick(line) : undefined}
            >
              <span className="font-mono text-[11px] text-ink-faint font-tabular w-[88px] shrink-0">
                {line.clock ?? (isDone ? "·" : isActive ? "…" : "·")}
              </span>
              <span
                className={clsx(
                  "font-mono text-[11px] uppercase w-[72px] shrink-0 border rounded-sm px-1 text-center",
                  verbChipClass(line.status),
                )}
              >
                {line.verb}
              </span>
              <span
                className={clsx(
                  "text-[13px] truncate flex-1",
                  isActive ? "text-ink" : isDone ? "text-ink-muted" : "text-ink-faint",
                )}
              >
                {line.body}
              </span>
              {running && isActive ? (
                <span className="tape-live-dot shrink-0" aria-label="In progress" />
              ) : isDone ? (
                <span className="font-mono text-[10px] text-sage-600 uppercase w-8 text-right shrink-0">ok</span>
              ) : typeof line.status === "string" && line.status !== "pending" && line.status !== "active" ? (
                <span className="font-mono text-[10px] text-ink-faint uppercase shrink-0">{line.status}</span>
              ) : null}
            </Row>
          );
        })}
        {lines.length === 0 ? (
          <div className="px-3 py-4 flex items-center gap-2 text-[12px] text-ink-faint">
            {running ? <span className="tape-live-dot shrink-0" aria-hidden /> : null}
            <span>{running ? emptyLabel : emptyLabel}</span>
          </div>
        ) : null}
      </div>
    </div>
  );
}
