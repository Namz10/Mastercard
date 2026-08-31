import { useEffect, useRef, useState } from "react";
import clsx from "clsx";
import type { SourceMode } from "@/lib/session-store";
import { useSessionSnapshot } from "@/lib/session-store";
import { useHonestyProbe } from "@/hooks/useHonestyProbe";
import { formatCapturedIst } from "@/lib/format";

const MODE_LABEL: Record<SourceMode, string> = {
  live: "LIVE",
  recorded: "RECORDED",
  frozen: "FROZEN",
  rules: "RULES",
};

function suffixFor(mode: SourceMode, capturedAt: Date | null): string {
  if (mode === "live") return "search + LLM";
  if (mode === "frozen") return "locked holdout";
  if (mode === "rules") return "policy table";
  return formatCapturedIst(capturedAt ?? new Date());
}

export function ModeChip({ mode, className }: { mode: SourceMode; className?: string }) {
  const session = useSessionSnapshot();
  const probe = useHonestyProbe();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    window.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const hollow = mode === "recorded";

  return (
    <div ref={ref} className={clsx("relative", className)}>
      <button
        type="button"
        className="inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-wide"
        data-testid="source-chip"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span
          className={clsx(
            "inline-flex items-center gap-1.5 h-5 px-2 rounded-sm border min-w-[8ch] justify-center transition-colors duration-100",
            mode === "live" && "border-accent/40 text-accent bg-accent-muted rounded-full",
            mode === "recorded" && "border-slate-600/40 text-slate-600 bg-surface-solid rounded-full",
            mode === "frozen" && "border-slate-600/40 text-slate-600 bg-surface-solid rounded-full",
            mode === "rules" && "border-signal-watch text-signal-watch bg-surface-solid rounded-full",
          )}
        >
          <span
            className={clsx(
              "w-1.5 h-1.5 rounded-full shrink-0",
              hollow ? "border border-current bg-transparent" : "bg-current",
            )}
            aria-hidden
          />
          <span className="min-w-[8ch] text-center">{MODE_LABEL[mode]}</span>
        </span>
        <span className="text-ink-faint normal-case tracking-normal hidden lg:inline truncate max-w-[20ch]">
          {suffixFor(mode, null)}
        </span>
      </button>
      {open ? (
        <div
          className="absolute left-0 top-[calc(100%+6px)] z-50 w-[280px] glass-sheet rounded-drawer p-3 text-[12px]"
          role="dialog"
          aria-label="Source honesty"
        >
          <Row k="Mode" v={MODE_LABEL[mode]} />
          <Row k="Tavily" v={probe.tavily ? "configured" : "not configured"} yes={probe.tavily} />
          <Row k="LLM" v={probe.llm ? "configured" : "not configured"} yes={probe.llm} />
          <Row k="Last reason" v={session.ui.recordedReason ?? "—"} />
        </div>
      ) : null}
    </div>
  );
}

function Row({ k, v, yes }: { k: string; v: string; yes?: boolean }) {
  return (
    <div className="flex justify-between gap-3 py-1.5 border-b border-border last:border-0">
      <span className="text-ink-faint">{k}</span>
      <span
        className={clsx(
          "font-mono text-right",
          yes === true && "text-sage-600",
          yes === false && "text-slate-600",
          yes == null && "text-ink",
        )}
      >
        {v}
      </span>
    </div>
  );
}

export function StatusStrip() {
  return null;
}
