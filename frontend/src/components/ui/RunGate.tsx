import type { ReactNode } from "react";
import clsx from "clsx";
import { Button } from "@/components/ui/Button";

/** Machinery empty state — one verb, one CTA, no stale chrome. */
export function RunGate({
  verb,
  title,
  body,
  onRun,
  runLabel,
  running = false,
  runningDetail,
  disabled = false,
  demoId,
  footer,
  variant = "default",
}: {
  verb: string;
  title: string;
  body: string;
  onRun?: () => void;
  runLabel: string;
  running?: boolean;
  runningDetail?: string;
  disabled?: boolean;
  demoId?: string;
  footer?: ReactNode;
  variant?: "default" | "block";
}) {
  return (
    <div
      className={clsx(
        "run-gate bento-panel workspace-card-lift flex-1 min-h-[420px] flex flex-col overflow-hidden",
        variant === "block" && "run-gate-block",
      )}
    >
      <div className="run-gate-scanline pointer-events-none" aria-hidden />
      <div className="px-5 py-4 border-b border-border/60 flex items-center gap-3 shrink-0">
        <span className="font-mono text-[11px] uppercase border border-ink/20 bg-sage-100/50 text-ink px-2 py-0.5 rounded-sm">
          {verb}
        </span>
        {running ? <span className="tape-live-dot" aria-hidden /> : null}
        <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint ml-auto">
          {running ? "in flight" : "awaiting operator"}
        </span>
      </div>
      <div className="flex-1 flex flex-col items-center justify-center px-8 py-10 text-center gap-5">
        <h2 className="font-serif text-[28px] sm:text-[32px] font-medium text-ink tracking-tight leading-tight max-w-lg">
          {title}
        </h2>
        <p className="text-[14px] text-ink-muted leading-relaxed max-w-md">{body}</p>
        {running && runningDetail ? (
          <p className="font-mono text-[13px] text-sage-700 tabular-nums">{runningDetail}</p>
        ) : null}
        {onRun ? (
          <Button
            variant="primary"
            className="h-11 px-8 mt-1"
            disabled={disabled || running}
            onClick={onRun}
            data-demo={demoId}
          >
            {runLabel}
          </Button>
        ) : null}
        {footer}
      </div>
    </div>
  );
}
