import { useNavigate } from "react-router-dom";
import clsx from "clsx";

const PHASES = [
  {
    id: "identify",
    label: "Identify",
    subtitle: "LangGraph · Tavily · pgvector · PostgreSQL HITL",
    to: "/identify",
  },
  {
    id: "generate",
    label: "Generate",
    subtitle: "ShadowRail · PyArrow Parquet · fidelity gate",
    to: "/simulation",
  },
  {
    id: "defend",
    label: "Defend",
    subtitle: "HistGradientBoosting · v0 rules · Brake",
    to: "/decisioning",
  },
  {
    id: "evolve",
    label: "Evolve",
    subtitle: "Loop M · G-test new seed · train-only extras",
    to: "/arms-race",
  },
] as const;

function isActive(status: string | undefined): boolean {
  return status === "active" || status === "running";
}

function isComplete(status: string | undefined): boolean {
  return status === "complete" || status === "completed";
}

function isError(status: string | undefined): boolean {
  return status === "error" || status === "failed";
}

export function ClosedLoopDiagram({
  phaseStatus,
}: {
  phaseStatus: Record<string, string>;
}) {
  const navigate = useNavigate();

  return (
    <section className="bg-white border border-border rounded-xl p-5 mb-8">
      <div className="font-mono uppercase text-ink-faint text-xs tracking-wide mb-1">Closed loop</div>
      <p className="text-xs text-ink-muted mb-5">
        Identify → Generate → Defend → Evolve · feedback via Loop C scout topics
      </p>

      <div className="relative pt-10">
        {/* Loop C feedback: Evolve → Identify (proper arc + arrowhead) */}
        <svg
          className="pointer-events-none absolute left-[6%] right-[6%] top-0 h-10 w-[88%]"
          viewBox="0 0 400 40"
          preserveAspectRatio="none"
          aria-hidden
        >
          <defs>
            <marker
              id="loop-c-arrow"
              markerWidth="8"
              markerHeight="8"
              refX="6"
              refY="4"
              orient="auto"
              markerUnits="strokeWidth"
            >
              <path d="M0,0 L8,4 L0,8 Z" fill="#166534" />
            </marker>
          </defs>
          <path
            d="M 380 28 C 380 6, 20 6, 20 28"
            fill="none"
            stroke="#166534"
            strokeWidth="1.75"
            strokeDasharray="6 4"
            markerEnd="url(#loop-c-arrow)"
            opacity="0.85"
          />
        </svg>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {PHASES.map((phase, i) => {
            const status = phaseStatus[phase.id];
            const active = isActive(status);
            const complete = isComplete(status);
            const errored = isError(status);

            return (
              <button
                key={phase.id}
                type="button"
                onClick={() => navigate(phase.to)}
                className={clsx(
                  "relative text-left rounded-xl border px-4 py-3.5 transition-colors hover:bg-surface-sunken",
                  active && "border-[#166534] bg-green-50 ring-1 ring-[#166534]/25",
                  complete && !active && "border-[#166534]/40 bg-white",
                  errored && "border-signal-block bg-red-50",
                  !active && !complete && !errored && "border-border bg-white",
                )}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className={clsx(
                      "inline-flex h-2 w-2 rounded-full shrink-0",
                      active && "bg-[#166534] animate-pulse",
                      complete && !active && "bg-[#166534]",
                      errored && "bg-signal-block",
                      !active && !complete && !errored && "bg-border-strong",
                    )}
                  />
                  <span className="font-mono text-xs font-semibold tracking-wide uppercase text-ink">
                    {phase.label}
                  </span>
                  {i < PHASES.length - 1 ? (
                    <span className="ml-auto font-mono text-[10px] text-ink-faint hidden lg:inline">
                      →
                    </span>
                  ) : null}
                </div>
                <div className="text-xs text-ink-muted leading-snug">{phase.subtitle}</div>
                <div className="mt-2 font-mono text-[10px] uppercase tracking-wide text-ink-faint">
                  {status || "idle"}
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </section>
  );
}
