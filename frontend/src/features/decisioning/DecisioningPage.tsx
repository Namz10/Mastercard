import { PageHeader } from "@/components/layout/Topbar";
import { Button } from "@/components/ui/Button";
import { ActionHistogram } from "./ActionHistogram";
import { ReasonCodes } from "./ReasonCodes";
import { ScoreSummary } from "./ScoreSummary";
import { useDecisioning } from "./useDecisioning";

export function DecisioningPage() {
  const { fit, score, runId, scoreData } = useDecisioning();
  const metrics = scoreData?.metrics ?? null;

  return (
    <div>
      <PageHeader
        title="Decisioning"
        actions={
          <>
            <span className="text-xs font-mono text-ink-faint hidden sm:inline">
              {runId ? `run: ${runId}` : "no run_id"}
            </span>
            <Button
              variant="secondary"
              disabled={!runId || fit.isPending}
              onClick={() => fit.mutate()}
              data-demo="defend-fit"
            >
              {fit.isPending ? "Fitting…" : "Fit model"}
            </Button>
            <Button
              variant="primary"
              disabled={!runId || score.isPending}
              onClick={() => score.mutate()}
              data-demo="defend-score"
            >
              {score.isPending ? "Scoring…" : "Score run"}
            </Button>
          </>
        }
      />
      {fit.error || score.error ? (
        <p className="text-sm text-signal-block mb-4">
          {(fit.error as Error)?.message || (score.error as Error)?.message || "Fit or Score failed — please run population on the Simulation Console first."}
        </p>
      ) : !runId ? (
        <p className="text-sm text-ink-muted mb-4">No dataset run selected — run population on the Simulation Console first.</p>
      ) : null}
      <div className="space-y-6">
        <ScoreSummary metrics={metrics} />
        <ActionHistogram histogram={scoreData?.action_histogram ?? null} />
        <ReasonCodes features={metrics?.top_features ?? null} />
      </div>
    </div>
  );
}
