import clsx from "clsx";
import type { SourceMode } from "@/lib/session-store";
import { useSessionSnapshot } from "@/lib/session-store";
import { useHonestyProbe } from "@/hooks/useHonestyProbe";

const MODE_LABEL: Record<SourceMode, string> = {
  live: "LIVE",
  recorded: "RECORDED",
  frozen: "FROZEN",
  rules: "RULES",
};

const MODE_SUFFIX: Record<SourceMode, string> = {
  live: "search + LLM",
  recorded: "captured corpus",
  frozen: "locked holdout",
  rules: "policy table",
};

export function ModeChip({ mode, className }: { mode: SourceMode; className?: string }) {
  return (
    <div
      className={clsx(
        "inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-wide",
        className,
      )}
      data-testid="source-chip"
    >
      <span
        className={clsx(
          "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm border min-w-[8ch] justify-center transition-colors duration-100",
          mode === "live" && "border-sage-600 text-sage-600 bg-sage-100",
          mode === "recorded" && "border-slate-600 text-slate-600 bg-paper-1",
          mode === "frozen" && "border-slate-600 text-slate-600 bg-paper-1",
          mode === "rules" && "border-signal-watch text-signal-watch bg-paper-1",
        )}
      >
        <span className="w-1.5 h-1.5 rounded-full bg-current" aria-hidden />
        {MODE_LABEL[mode]}
      </span>
      <span className="text-ink-faint normal-case tracking-normal hidden md:inline">
        {MODE_SUFFIX[mode]}
      </span>
    </div>
  );
}

export function StatusStrip() {
  useHonestyProbe();
  const session = useSessionSnapshot();
  const run = session.generate.runId;
  const seed = session.generate.seed;

  return (
    <div className="h-8 shrink-0 border-b border-border bg-surface flex items-center px-6 gap-4 text-[11px] font-mono text-ink-faint">
      <ModeChip mode={session.ui.sourceChip} />
      <span className="text-hairline">·</span>
      {session.identify.runId ? <span>discover {session.identify.runId.slice(0, 12)}</span> : <span>discover —</span>}
      <span className="text-hairline">·</span>
      {run ? <span>sim {run.slice(0, 12)}</span> : <span>sim —</span>}
      <span className="text-hairline">·</span>
      {seed != null ? <span>seed {seed}</span> : <span>seed —</span>}
      {session.ui.recordedReason ? (
        <span className="ml-auto text-slate-600 truncate max-w-[40%]">{session.ui.recordedReason}</span>
      ) : null}
    </div>
  );
}
