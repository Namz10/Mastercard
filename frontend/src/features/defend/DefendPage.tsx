import { Link, useNavigate } from "react-router-dom";
import clsx from "clsx";
import type { ScoreMetrics } from "@/lib/api-types";
import { PageHeader } from "@/components/layout/Topbar";
import { Button } from "@/components/ui/Button";
import { ModeChip } from "@/components/ui/ModeChip";
import { AegisDefendStats } from "@/components/ui/advanced-stats";
import { COPY } from "@/lib/copy";
import { formatPct, worstApFamily } from "@/lib/format";
import { RecallFprCurve } from "@/features/decisioning/RecallFprCurve";
import { BrakeRail } from "./BrakeRail";
import { useDefend } from "./useDefend";

function DefendVerdictHero({
  metrics,
  scoring,
  sourceMode,
}: {
  metrics: ScoreMetrics | null;
  scoring: boolean;
  sourceMode: "live" | "recorded" | "frozen" | "rules";
}) {
  const recall = metrics ? (metrics.recall_at_op * 100).toFixed(2) : scoring ? "…" : "—";
  const fpr = metrics ? formatPct(metrics.genuine_fp, 3) : null;
  const hasScore = Boolean(metrics);

  return (
    <div
      className="defend-verdict-hero bento-panel mb-2.5 shrink-0 px-5 py-4 flex flex-col sm:flex-row sm:items-end gap-4 sm:gap-6"
      data-demo="defend-verdict"
    >
      <div className="min-w-0 flex-1">
        <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-faint mb-1">
          Recall @ operating point
        </p>
        <div className="flex items-baseline gap-3 flex-wrap">
          <span className="defend-verdict-number font-mono font-semibold text-ink font-tabular tracking-tight">
            {recall}
            {hasScore ? <span className="text-[0.45em] text-sage-600 ml-0.5">%</span> : null}
          </span>
          {fpr ? (
            <span className="font-mono text-[13px] text-ink-muted">
              @ genuine FPR <span className="text-ink font-medium">{fpr}</span>
            </span>
          ) : scoring ? (
            <span className="font-mono text-[13px] text-ink-faint animate-pulse motion-reduce:animate-none">
              {COPY.defend.scoring}…
            </span>
          ) : (
            <span className="text-[13px] text-ink-faint">{COPY.defend.empty}</span>
          )}
        </div>
        {hasScore ? (
          <p className="mt-1.5 text-[12px] text-ink-faint">{COPY.defend.frozen}</p>
        ) : null}
      </div>
      <div className="flex items-center gap-3 shrink-0">
        {hasScore ? (
          <span
            className={clsx(
              "defend-verdict-pass font-mono text-[11px] uppercase tracking-wide px-3 py-1.5 rounded-full border",
              metrics?.pass !== false
                ? "text-sage-700 bg-sage-100/90 border-sage-600/25"
                : "text-signal-block bg-surface border-signal-block/25",
            )}
          >
            {metrics?.pass !== false ? "Holdout pass" : "Below target"}
          </span>
        ) : null}
        <ModeChip mode={sourceMode} className="opacity-90" />
      </div>
    </div>
  );
}

export function DefendPage() {
  const navigate = useNavigate();
  const { session, score, overlayRetrain, retrain, retrainError, retrainLive, canRetrain } = useDefend();
  const metrics = session.defend.score?.metrics ?? null;
  const before = session.defend.scoreBeforeRetrain?.metrics ?? null;
  const scoring = score.isPending;
  const miss = session.defend.missTechniqueId;
  const missFamily = metrics ? worstApFamily(metrics.ap_by_family) : null;
  const hasBefore = Boolean(before);

  return (
    <div className="defend-atmosphere flex flex-col h-full min-h-0 relative -mx-4 -my-3 px-4 py-3">
      <PageHeader
        title={COPY.nav.defend}
        caption="Locked holdout · proof the model caught synthetic fraud"
        actions={
          <>
            <Button
              variant="secondary"
              disabled={score.isPending || !session.generate.runId}
              onClick={() => score.mutate()}
              title={!session.generate.runId ? COPY.defend.retrainDisabled : undefined}
            >
              {COPY.defend.recompute}
            </Button>
            <Button
              variant="secondary"
              disabled={!canRetrain || retrain.isPending}
              title={canRetrain ? COPY.defend.confirmRetrain : COPY.defend.retrainDisabled}
              onClick={() => void overlayRetrain()}
              data-demo="retrain"
            >
              {COPY.defend.retrain}
            </Button>
          </>
        }
      />

      <DefendVerdictHero metrics={metrics} scoring={scoring} sourceMode={session.ui.sourceChip} />

      <AegisDefendStats
        className="mb-2.5 shrink-0"
        metrics={metrics}
        before={before}
        scoring={scoring}
        missFamily={missFamily}
        missTechniqueId={miss}
        compact
        showHero={false}
      />

      {retrainLive ? (
        <p className="text-[13px] text-sage-600 mb-2 sage-flash">{COPY.defend.updated}</p>
      ) : null}
      {retrainError ? (
        <p className="text-[13px] text-slate-600 mb-2 border border-border bg-surface px-3 py-2 rounded-sheet">
          {retrainError}
        </p>
      ) : null}

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-[minmax(0,72fr)_minmax(0,28fr)] gap-3 min-h-0">
        <RecallFprCurve metrics={metrics} before={before} scoring={scoring} hasBefore={hasBefore} />
        <BrakeRail histogram={session.defend.score?.action_histogram ?? null} />
      </div>

      {retrainLive && miss ? (
        <footer className="glass-sheet sticky bottom-0 z-10 -mx-1 px-4 mt-2.5 shrink-0 h-12 flex items-center gap-3 rounded-sheet">
          <span className="text-[12px] text-ink-muted truncate">{COPY.defend.updated}</span>
          <div className="ml-auto">
            <Button variant="primary" onClick={() => navigate(`/?highlight=${miss}`)} data-demo="continue-identify">
              Continue to Identify
            </Button>
          </div>
        </footer>
      ) : metrics && session.generate.runId ? (
        <footer className="glass-sheet sticky bottom-0 z-10 -mx-1 px-4 mt-2.5 shrink-0 h-12 flex items-center gap-3 rounded-sheet">
          <span className="font-mono text-[11px] text-ink-faint tabular-nums">
            {metrics.n_eval.toLocaleString("en-IN")} holdout rows
          </span>
          <div className="ml-auto">
            <Link to="/identify">
              <Button variant="primary" data-demo="continue-identify-loop">
                Back to Identify
              </Button>
            </Link>
          </div>
        </footer>
      ) : null}
    </div>
  );
}
