import { NavLink, useLocation } from "react-router-dom";
import clsx from "clsx";
import { ModeChip } from "@/components/ui/ModeChip";
import { COPY } from "@/lib/copy";
import { phaseStatus, useSessionSnapshot } from "@/lib/session-store";

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

/** Row 1 of workspace chrome: FROZEN chip + phase stepper + ⌘K. Session hashes live in palette only. */
export function WorkspaceChrome() {
  const location = useLocation();
  const session = useSessionSnapshot();

  return (
    <div className="h-10 shrink-0 glass-sheet rounded-sheet flex items-center px-3 gap-2 text-[13px]">
      <ModeChip mode={session.ui.sourceChip} className="shrink-0" />
      <span className="text-hairline text-ink-faint hidden sm:inline" aria-hidden>
        ·
      </span>
      <nav className="flex items-center gap-0.5 min-w-0 flex-1" aria-label="Phases">
        {PHASES.map((phase, i) => {
          const status = phaseStatus(phase.id);
          const active = location.pathname === phase.to;
          const blocked = status === "idle" && phase.id !== "identify";
          return (
            <div key={phase.id} className="flex items-center gap-0.5">
              {i > 0 ? <span className="text-ink-faint px-1 opacity-35 hidden sm:inline">→</span> : null}
              <NavLink
                to={phase.to}
                title={blocked ? "Complete prior phase first" : undefined}
                className={clsx(
                  "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full transition-colors duration-100 text-[12px]",
                  active
                    ? "bg-accent text-accent-fg font-medium shadow-sm"
                    : "text-ink-muted hover:text-ink hover:bg-accent-muted",
                )}
              >
                <span
                  className={clsx("w-1.5 h-1.5 rounded-full shrink-0", active ? "bg-accent-fg" : STATUS_DOT[status])}
                  aria-hidden
                />
                <span className="truncate">{phase.label}</span>
              </NavLink>
            </div>
          );
        })}
      </nav>
      <button
        type="button"
        className="shrink-0 ml-auto font-mono text-[10px] text-ink-faint hover:text-ink px-2 py-1 rounded-md hover:bg-accent-muted transition-colors duration-100"
        data-demo="command-palette"
        onClick={() => window.dispatchEvent(new Event("aegis:toggle-palette"))}
        title="Ops commands"
      >
        ⌘K
      </button>
    </div>
  );
}
