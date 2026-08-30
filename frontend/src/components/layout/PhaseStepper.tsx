import { NavLink, useLocation } from "react-router-dom";
import clsx from "clsx";
import { COPY } from "@/lib/copy";
import { phaseStatus } from "@/lib/session-store";

const PHASES = [
  { id: "identify" as const, to: "/identify", label: COPY.nav.identify },
  { id: "generate" as const, to: "/generate", label: COPY.nav.generate },
  { id: "defend" as const, to: "/defend", label: COPY.nav.defend },
];

const STATUS_DOT: Record<string, string> = {
  idle: "bg-border",
  in_progress: "bg-signal-watch",
  ready: "bg-sage-600",
  done: "bg-sage-600",
};

const REASON: Record<string, string> = {
  identify: "",
  generate: "Add at least one attack to the catalog, or continue on catalog seed.",
  defend: "Defend after fidelity is known (pass or fail).",
};

export function PhaseStepper() {
  const location = useLocation();

  return (
    <div className="h-10 shrink-0 glass-sheet rounded-sheet flex items-center px-3 gap-1 text-[13px]">
      {PHASES.map((phase, i) => {
        const status = phaseStatus(phase.id);
        const active = location.pathname === phase.to;
        const blocked = status === "idle" && phase.id !== "identify";
        return (
          <div key={phase.id} className="flex items-center gap-1">
            {i > 0 ? <span className="text-ink-faint px-1.5 opacity-40">→</span> : null}
            <NavLink
              to={phase.to}
              title={blocked ? REASON[phase.id] : undefined}
              className={clsx(
                "inline-flex items-center gap-2 px-3 py-1.5 rounded-full transition-colors duration-100",
                active
                  ? "bg-accent text-accent-fg font-medium shadow-sm"
                  : "text-ink-muted hover:text-ink hover:bg-accent-muted",
              )}
            >
              <span
                className={clsx("w-1.5 h-1.5 rounded-full", active ? "bg-accent-fg" : STATUS_DOT[status])}
                aria-hidden
              />
              {phase.label}
            </NavLink>
          </div>
        );
      })}
    </div>
  );
}
