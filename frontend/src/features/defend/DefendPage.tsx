import { useNavigate } from "react-router-dom";
import { PageHeader } from "@/components/layout/Topbar";
import { Button } from "@/components/ui/Button";
import { COPY } from "@/lib/copy";
import { formatPct } from "@/lib/format";
import { RecallFprCurve } from "@/features/decisioning/RecallFprCurve";
import { BrakeRail } from "./BrakeRail";
import { useDefend } from "./useDefend";

export function DefendPage() {
  const navigate = useNavigate();
  const { session, score, overlayRetrain, retrain } = useDefend();
  const metrics = session.defend.score?.metrics ?? null;
  const before = session.defend.scoreBeforeRetrain?.metrics ?? null;
  const scoring = score.isPending;
  const miss = session.defend.missTechniqueId;

  return (
    <div className="flex flex-col h-[calc(100vh-88px)] min-h-0">
      <PageHeader
        title={COPY.nav.defend}
        caption={COPY.defend.holdoutCaveat}
        actions={
          <>
            <Button variant="secondary" disabled={score.isPending || !session.generate.runId} onClick={() => score.mutate()}>
              {COPY.defend.recompute}
            </Button>
            {metrics ? (
              <Button
                variant="primary"
                disabled={retrain.isPending}
                onClick={() => void overlayRetrain()}
                data-demo="retrain"
              >
                {COPY.defend.retrain}
              </Button>
            ) : null}
            {miss ? (
              <Button variant="primary" onClick={() => navigate(`/?highlight=${miss}`)} data-demo="continue-identify">
                Continue to Identify
              </Button>
            ) : null}
          </>
        }
      />

      <div className="h-12 shrink-0 grid grid-cols-4 gap-px bg-border border border-border mb-2">
        <Kpi label="At operating point" value={metrics ? `${(metrics.recall_at_op * 100).toFixed(1)}%` : "—"} hint={metrics ? `${formatPct(metrics.genuine_fp, 3)} genuine FPR` : undefined} />
        <Kpi label="Ranking (threshold-free)" value={metrics ? metrics.binary_ap.toFixed(3) : "—"} />
        <Kpi label="Precision @ OP" value={metrics ? formatPct(metrics.precision_at_op) : "—"} hint={metrics ? `F1 ${metrics.f1_at_op.toFixed(3)}` : undefined} />
        <Kpi label="Eval world" value={metrics ? `${metrics.n_eval.toLocaleString("en-IN")} rows` : "—"} hint="holdout" />
      </div>

      {scoring ? (
        <p className="text-[13px] font-mono text-ink-muted mb-2">{COPY.defend.scoring}</p>
      ) : null}

      {session.defend.loopResult ? (
        <p className="text-[13px] text-sage-600 mb-2">{COPY.defend.updated}</p>
      ) : null}

      <div className="flex-1 grid grid-cols-[72%_28%] gap-3 min-h-0">
        {metrics ? (
          <RecallFprCurve metrics={metrics} before={before} />
        ) : (
          <div className="border border-border rounded bg-surface flex items-center justify-center text-[13px] text-ink-faint px-6 text-center">
            {COPY.defend.empty}
          </div>
        )}
        <BrakeRail histogram={session.defend.score?.action_histogram ?? null} />
      </div>
    </div>
  );
}

function Kpi({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="bg-surface px-3 py-1.5 flex flex-col justify-center">
      <div className="text-[11px] text-ink-faint">{label}</div>
      <div className="font-mono text-[18px] text-ink font-tabular leading-tight">{value}</div>
      {hint ? <div className="text-[11px] text-ink-faint">{hint}</div> : null}
    </div>
  );
}
