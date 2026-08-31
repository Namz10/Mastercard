import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { JobThread } from "@/components/ui/JobThread";
import { StageShell } from "@/components/layout/StageShell";
import { StickyContinue } from "@/components/layout/StickyContinue";
import { COPY } from "@/lib/copy";
import { worstApFamily } from "@/lib/format";
import { RecallFprCurve } from "@/features/decisioning/RecallFprCurve";
import { useDefend } from "./useDefend";
import { FeedbackVerdict } from "./FeedbackVerdict";

export function FeedbackPage() {
  const { session, retrain } = useDefend();
  const [error, setError] = useState<string | null>(null);
  const metrics = session.defend.score?.metrics ?? null;
  const before = session.defend.scoreBeforeRetrain?.metrics ?? null;
  const loopDone = Boolean(session.defend.loopResult);
  const miss = session.defend.missTechniqueId;
  const missFamily = metrics ? worstApFamily(metrics.ap_by_family) : "app_fraud";

  const onRunLoop = async () => {
    setError(null);
    try {
      await retrain.mutateAsync();
    } catch {
      setError(COPY.defend.feedbackFail);
    }
  };

  return (
    <StageShell
      title={COPY.stages.feedback}
      caption={COPY.defend.feedbackCaption}
      actions={
        !loopDone && !retrain.isPending ? (
          <Button
            variant="primary"
            disabled={!session.defend.score}
            onClick={() => void onRunLoop()}
            data-demo="run-feedback-loop"
          >
            {COPY.defend.feedbackLoop}
          </Button>
        ) : undefined
      }
      footer={
        loopDone ? (
          <StickyContinue
            to="/defend/hyperparameters"
            label={COPY.defend.continueOptuna}
            demoId="continue-optuna"
            secondary={
              <Link
                to={miss ? `/identify?highlight=${miss}` : "/identify"}
                className="text-[13px] text-ink-muted hover:text-ink underline-offset-2 hover:underline"
              >
                {COPY.defend.backIdentify}
              </Link>
            }
          />
        ) : undefined
      }
    >
      <p className="text-[13px] text-ink-muted mb-2 max-w-prose">{COPY.defend.feedbackBody}</p>
      {error ? <ErrorBanner message={error} onRetry={() => void onRunLoop()} /> : null}

      {retrain.isPending || retrain.stream.running ? (
        <div className="flex-1 min-h-[420px] flex flex-col">
          <JobThread
            lines={retrain.stream.lines}
            running
            title="Feedback loop"
            emptyLabel={COPY.defend.feedbackRunning}
          />
        </div>
      ) : loopDone && metrics && before ? (
        <div className="booth-crossfade-enter flex-1 min-h-[420px] grid grid-cols-1 lg:grid-cols-[minmax(0,40fr)_minmax(0,60fr)] gap-4">
          <FeedbackVerdict missFamily={missFamily} before={before} after={metrics} />
          <RecallFprCurve metrics={metrics} before={before} hasBefore dualOp fixedY />
        </div>
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center gap-4 px-6">
          <Button
            variant="primary"
            className="h-11 px-8"
            disabled={!session.defend.score}
            onClick={() => void onRunLoop()}
            data-demo="run-feedback-loop"
          >
            {COPY.defend.feedbackLoop}
          </Button>
        </div>
      )}
    </StageShell>
  );
}
