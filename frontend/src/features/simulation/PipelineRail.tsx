import clsx from "clsx";
import {
  PIPELINE_PHASES,
  type LabPhase,
  type LoopMarker,
  type PhaseStatus,
  type PhaseStatusMap,
} from "./lab-types";

const STATUS_STYLES: Record<PhaseStatus, string> = {
  pending: "border-border text-ink-faint bg-surface",
  active: "border-[#166534] text-[#166534] bg-green-50",
  completed: "border-[#166534]/50 text-[#166534] bg-surface",
  failed: "border-signal-block text-signal-block bg-red-50",
};

function PhaseGlyph({ status }: { status: PhaseStatus }) {
  if (status === "completed") {
    return (
      <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-[#166534] text-white text-[10px]">
        ✓
      </span>
    );
  }
  if (status === "failed") {
    return (
      <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-signal-block text-white text-[10px]">
        !
      </span>
    );
  }
  if (status === "active") {
    return (
      <span className="inline-flex h-5 w-5 items-center justify-center rounded-full border-2 border-[#166534]">
        <span className="h-2 w-2 rounded-full bg-[#166534] animate-pulse" />
      </span>
    );
  }
  return <span className="inline-flex h-5 w-5 rounded-full border border-border-strong bg-surface-sunken" />;
}

export function PipelineRail({
  phaseStatus,
  runId,
  threadId,
  generation,
  loopMarkers,
  onPhaseClick,
}: {
  phaseStatus: PhaseStatusMap;
  runId: string | null;
  threadId: string;
  generation: string;
  loopMarkers: LoopMarker[];
  onPhaseClick: (phase: Exclude<LabPhase, "system">) => void;
}) {
  return (
    <div className="sticky top-0 z-20 -mx-1 mb-4 bg-bg/95 backdrop-blur-sm border-b border-border pb-3 pt-1">
      <div className="flex flex-wrap items-stretch gap-2">
        {PIPELINE_PHASES.map((phase, i) => {
          const status = phaseStatus[phase.id];
          return (
            <button
              key={phase.id}
              type="button"
              onClick={() => onPhaseClick(phase.id)}
              className={clsx(
                "flex-1 min-w-[140px] text-left rounded border px-3 py-2.5 transition-colors hover:bg-surface-sunken",
                STATUS_STYLES[status],
              )}
            >
              <div className="flex items-center gap-2 mb-1">
                <PhaseGlyph status={status} />
                <span className="font-mono text-xs font-semibold tracking-wide">{phase.label}</span>
                {i < PIPELINE_PHASES.length - 1 ? (
                  <span className="ml-auto font-mono text-[10px] text-ink-faint hidden sm:inline">→</span>
                ) : null}
              </div>
              <div className="flex flex-wrap gap-1 mt-1">
                {phase.badges.map((b) => (
                  <span
                    key={b}
                    className="font-mono text-[10px] px-1.5 py-0.5 rounded-sm border border-current/20 opacity-80"
                  >
                    {b}
                  </span>
                ))}
              </div>
            </button>
          );
        })}
      </div>

      <div className="mt-2 font-mono text-[11px] text-ink-muted">
        run_id={runId ?? "—"} · thread_id={threadId} · generation={generation}
      </div>

      <div className="mt-2">
        <div className="font-mono text-[10px] uppercase tracking-wide text-ink-faint mb-1">Loop timeline</div>
        <div className="flex items-center gap-1 overflow-x-auto pb-0.5">
          {loopMarkers.length === 0 ? (
            <span className="font-mono text-[11px] text-ink-faint">waiting for Loop C / I / M markers…</span>
          ) : (
            loopMarkers.map((m) => (
              <span
                key={`${m.index}-${m.loop}-${m.kind}`}
                className={clsx(
                  "shrink-0 font-mono text-[10px] px-2 py-1 rounded border",
                  m.kind === "open"
                    ? "border-[#166534] text-[#166534] bg-green-50"
                    : m.pass === false
                      ? "border-signal-block text-signal-block"
                      : "border-border text-ink-muted bg-surface",
                )}
                title={`${m.phase} · ${m.ts}`}
              >
                {m.kind === "open" ? "▸" : "◂"} Loop {m.loop}
                {m.kind === "close" && m.pass != null ? (m.pass ? " ✓" : " ✗") : ""}
              </span>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
