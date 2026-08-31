import { NavLink, useLocation } from "react-router-dom";
import clsx from "clsx";
import {
  defendStageLabel,
  defendStageUnlocked,
  identifyStageLabel,
  identifyStageUnlocked,
  previousDefendStage,
  previousIdentifyStage,
  type DefendStage,
  type IdentifyStage,
} from "@/lib/stage-unlock";
import { useSessionSnapshot } from "@/lib/session-store";

const IDENTIFY_STAGES: IdentifyStage[] = ["landscape", "discover", "review"];
const DEFEND_STAGES: DefendStage[] = ["detection", "interventions", "feedback", "hyperparameters"];

function pillPath(pillar: "identify" | "defend", stage: string): string {
  if (pillar === "identify") {
    return stage === "landscape" ? "/identify" : `/identify/${stage}`;
  }
  return `/defend/${stage}`;
}

export function StagePills() {
  const location = useLocation();
  const session = useSessionSnapshot();

  const identify = location.pathname.startsWith("/identify");
  const defend = location.pathname.startsWith("/defend");
  if (!identify && !defend) return null;

  const stages = identify ? IDENTIFY_STAGES : DEFEND_STAGES;
  const pillar = identify ? "identify" : "defend";

  return (
    <nav className="flex items-center gap-1 min-w-0 overflow-x-auto" aria-label="Stage navigation">
      {stages.map((stage, i) => {
        const path = pillPath(pillar, stage);
        const active =
          pillar === "identify"
            ? stage === "landscape"
              ? location.pathname === "/identify"
              : location.pathname.startsWith(path)
            : location.pathname.startsWith(path);
        const unlocked =
          pillar === "identify"
            ? identifyStageUnlocked(stage as IdentifyStage, session)
            : defendStageUnlocked(stage as DefendStage, session);
        const prev =
          pillar === "identify"
            ? previousIdentifyStage(stage as IdentifyStage)
            : previousDefendStage(stage as DefendStage);
        const prevLabel = prev
          ? pillar === "identify"
            ? identifyStageLabel(prev as IdentifyStage)
            : defendStageLabel(prev as DefendStage)
          : "";
        const label = pillar === "identify" ? identifyStageLabel(stage as IdentifyStage) : defendStageLabel(stage as DefendStage);

        return (
          <div key={stage} className="flex items-center gap-1 shrink-0">
            {i > 0 ? <span className="text-ink-faint opacity-35 px-0.5">·</span> : null}
            <NavLink
              to={path}
              title={unlocked ? undefined : `Finish ${prevLabel} first`}
              data-demo={`stage-pill-${stage}`}
              className={({ isActive }) =>
                clsx(
                  "inline-flex items-center px-2 py-0.5 rounded-full text-[11px] transition-colors duration-100",
                  isActive || active
                    ? "bg-sage-100 text-sage-700 font-medium"
                    : unlocked
                      ? "text-ink-muted hover:text-ink hover:bg-accent-muted"
                      : "text-ink-faint opacity-50 pointer-events-none",
                )
              }
              onClick={(e) => {
                if (!unlocked) e.preventDefault();
              }}
            >
              {label}
            </NavLink>
          </div>
        );
      })}
    </nav>
  );
}
