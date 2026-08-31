import clsx from "clsx";
import type { ScoreMetrics } from "@/lib/api-types";
import { COPY } from "@/lib/copy";
import { formatPct } from "@/lib/format";

export function MetricHero({
  metrics,
  scoring,
  className,
}: {
  metrics: ScoreMetrics | null;
  scoring?: boolean;
  className?: string;
}) {
  const recall = metrics ? (metrics.recall_at_op * 100).toFixed(2) : scoring ? "…" : "—";
  const fpr = metrics ? formatPct(metrics.genuine_fp, 3) : null;
  const hasScore = Boolean(metrics);

  return (
    <div
      className={clsx(
        "defend-verdict-hero bento-panel shrink-0 px-5 py-4 flex flex-col sm:flex-row sm:items-end gap-4 sm:gap-6",
        className,
      )}
      data-demo="metric-hero"
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
            <span className="font-mono text-[13px] text-ink-faint">{COPY.defend.scoring}…</span>
          ) : (
            <span className="text-[13px] text-ink-faint">{COPY.defend.empty}</span>
          )}
        </div>
      </div>
    </div>
  );
}
