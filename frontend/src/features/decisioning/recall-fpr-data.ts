import type { ScoreMetrics } from "@/lib/api-types";

export interface RecallFprPoint {
  fprLabel: string;
  fprPct: number;
  recall: number;
  beforeRecall?: number;
}

function readTpr(tprAtFpr: ScoreMetrics["tpr_at_fpr"], key: string): number | null {
  const entry = tprAtFpr?.[key];
  if (entry == null) return null;
  if (typeof entry === "number") return entry;
  if (typeof entry === "object" && "tpr" in entry) return (entry as { tpr: number }).tpr;
  return null;
}

function pointsFrom(metrics: ScoreMetrics): { label: string; pct: number; recall: number }[] {
  const anchors: { label: string; pct: number; key: string | null }[] = [
    { label: "0.05", pct: 0.05, key: "0.0005" },
    { label: "0.1", pct: 0.1, key: "0.001" },
    { label: "0.5", pct: 0.5, key: "0.005" },
    { label: "1", pct: 1, key: "0.01" },
    { label: "5", pct: 5, key: "0.05" },
  ];
  const known = anchors
    .map((a) => ({ ...a, tpr: a.key ? readTpr(metrics.tpr_at_fpr, a.key) : null }))
    .filter((a) => a.tpr != null) as { label: string; pct: number; tpr: number }[];

  const opRecall = metrics.recall_at_op;
  if (known.length === 0 && opRecall != null) {
    const opFprPct = Math.max(0.02, metrics.genuine_fp * 100);
    return [{ label: opFprPct.toFixed(2), pct: opFprPct, recall: opRecall * 100 }];
  }

  const interpolate = (pct: number): number => {
    if (known.length === 0) return (opRecall ?? 0) * 100;
    if (pct <= known[0].pct) return known[0].tpr * 100;
    if (pct >= known[known.length - 1].pct) return known[known.length - 1].tpr * 100;
    for (let i = 0; i < known.length - 1; i++) {
      const lo = known[i];
      const hi = known[i + 1];
      if (pct >= lo.pct && pct <= hi.pct) {
        const t = (pct - lo.pct) / (hi.pct - lo.pct);
        return (lo.tpr + t * (hi.tpr - lo.tpr)) * 100;
      }
    }
    return known[known.length - 1].tpr * 100;
  };

  return anchors.map((a) => ({
    label: a.label,
    pct: a.pct,
    recall: interpolate(a.pct),
  }));
}

/** Single series unless `before` is a real score. Never invent a 0.84× baseline. */
export function buildRecallFprCurve(
  metrics: ScoreMetrics,
  before?: ScoreMetrics | null,
): RecallFprPoint[] {
  const after = pointsFrom(metrics);
  const beforePts = before ? pointsFrom(before) : null;
  return after.map((p) => ({
    fprLabel: p.label,
    fprPct: p.pct,
    recall: p.recall,
    beforeRecall: beforePts?.find((b) => b.pct === p.pct)?.recall,
  }));
}

export function opPoint(metrics: ScoreMetrics) {
  return {
    recallPct: metrics.recall_at_op * 100,
    fprPct: metrics.genuine_fp * 100,
    threshold: metrics.op_threshold,
  };
}
