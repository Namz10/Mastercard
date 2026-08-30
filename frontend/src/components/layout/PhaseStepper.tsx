import { NavLink, useLocation } from "react-router-dom";
import clsx from "clsx";
import { COPY } from "@/lib/copy";
import { phaseStatus } from "@/lib/session-store";

const PHASES = [
  { id: "identify" as const, to: "/", label: COPY.nav.identify },
  { id: "generate" as const, to: "/generate", label: COPY.nav.generate },
  { id: "defend" as const, to: "/defend", label: COPY.nav.defend },
];

const STATUS_DOT: Record<string, string> = {
  idle: "bg-border",
  in_progress: "bg-signal-watch",
  ready: "bg-sage-600",
  done: "bg-sage-600",
};

export function PhaseStepper() {
  const location = useLocation();

  return (
    <div className="h-9 shrink-0 border-b border-border bg-surface flex items-center px-6 gap-1 text-[13px]">
      {PHASES.map((phase, i) => {
        const status = phaseStatus(phase.id);
        const active = location.pathname === phase.to || (phase.to === "/" && location.pathname === "/");
        return (
          <div key={phase.id} className="flex items-center gap-1">
            {i > 0 ? <span className="text-ink-faint px-1">→</span> : null}
            <NavLink
              to={phase.to}
              className={clsx(
                "inline-flex items-center gap-1.5 px-2 py-1 rounded-sm transition-colors duration-100",
                active ? "text-ink font-medium" : "text-ink-muted hover:text-ink",
              )}
            >
              <span className={clsx("w-1.5 h-1.5 rounded-full", STATUS_DOT[status])} aria-hidden />
              {phase.label}
            </NavLink>
          </div>
        );
      })}
    </div>
  );
}
