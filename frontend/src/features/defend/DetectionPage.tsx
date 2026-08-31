import { useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { JobThread } from "@/components/ui/JobThread";
import { RunGate } from "@/components/ui/RunGate";
import { MetricHero } from "@/components/ui/MetricHero";
import { StageShell } from "@/components/layout/StageShell";
import { StickyContinue } from "@/components/layout/StickyContinue";
import { COPY } from "@/lib/copy";
import { RecallFprCurve } from "@/features/decisioning/RecallFprCurve";
import {
  canScoreGenerate,
  clearDefendIfStale,
  isDefendScoreCurrent,
  useSessionSnapshot,
} from "@/lib/session-store";
import { useDefend } from "./useDefend";

export function DetectionPage() {
  const session = useSessionSnapshot();
  const navigate = useNavigate();
  const { score } = useDefend();
  const scoring = score.isPending || score.stream.running;
  const booted = useRef(false);
  const canScore = canScoreGenerate(session);
  const scoreCurrent = isDefendScoreCurrent(session);
  const metrics = scoreCurrent ? session.defend.score?.metrics ?? null : null;

  useEffect(() => {
    clearDefendIfStale();
  }, []);

  useEffect(() => {
    if (booted.current) return;
    if (!canScore) return;
    if (metrics) return;
    booted.current = true;
    void score.mutate();
  }, [canScore, metrics, score]);

  return (
    <StageShell
      title={COPY.stages.detection}
      caption={COPY.defend.detectionCaption}
      secondaryActions={
        metrics ? (
          <Button
            variant="secondary"
            disabled={score.isPending || !canScore}
            onClick={() => score.mutate()}
          >
            {COPY.defend.recompute}
          </Button>
        ) : undefined
      }
      footer={
        metrics ? (
          <StickyContinue
            to="/defend/interventions"
            label={COPY.defend.continueInterventions}
            demoId="continue-interventions"
          />
        ) : undefined
      }
    >
      {score.error ? (
        <ErrorBanner
          message={COPY.defend.scoreFail}
          onRetry={() => {
            booted.current = true;
            score.mutate();
          }}
          hint="⌘K for locked holdout"
        />
      ) : null}

      {!session.generate.runId ? (
        <RunGate
          verb="SCORE"
          title="Score on a simulated corpus first"
          body={COPY.defend.empty}
          runLabel="Go to Generate"
          onRun={() => navigate("/generate")}
          demoId="detection-needs-generate"
          footer={
            <Link to="/generate" className="text-[12px] text-ink-faint hover:text-ink underline-offset-2 hover:underline">
              Simulate payment traffic
            </Link>
          }
        />
      ) : scoring || !metrics ? (
        <div className="flex-1 flex flex-col min-h-0">
          <JobThread
            lines={score.stream.lines}
            running={scoring}
            title="Fit & score"
            emptyLabel={COPY.defend.scoring}
          />
        </div>
      ) : (
        <div className="booth-crossfade-enter flex-1 flex flex-col min-h-0">
          <MetricHero metrics={metrics} />
          <div className="flex-1 min-h-[420px] mt-2">
            <RecallFprCurve metrics={metrics} />
          </div>
        </div>
      )}
    </StageShell>
  );
}
