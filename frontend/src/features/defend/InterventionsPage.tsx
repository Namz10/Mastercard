import { StageShell } from "@/components/layout/StageShell";
import { StickyContinue } from "@/components/layout/StickyContinue";
import { COPY } from "@/lib/copy";
import { useSessionSnapshot, isDefendScoreCurrent } from "@/lib/session-store";
import { BrakeRail } from "./BrakeRail";

export function InterventionsPage() {
  const session = useSessionSnapshot();
  const hasScore = isDefendScoreCurrent(session);

  return (
    <StageShell
      title={COPY.stages.interventions}
      caption={COPY.defend.interventionsCaption}
      footer={
        hasScore ? (
          <StickyContinue
            to="/defend/feedback"
            label={COPY.defend.continueFeedback}
            demoId="continue-feedback"
          />
        ) : undefined
      }
    >
      <div className="flex-1 min-h-0">
        <BrakeRail
          histogram={session.defend.score?.action_histogram ?? null}
          metrics={session.defend.score?.metrics ?? null}
        />
      </div>
    </StageShell>
  );
}
