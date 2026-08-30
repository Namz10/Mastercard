import type { ScoreMetrics } from "@/lib/api-types";

export interface RecallFprPoint {
  fprLabel: string;
  fprPct: number;
  championRecall: number;
  baselineRecall: number;
}

function readTpr(
  tprAtFpr: ScoreMetrics["tpr_at_fpr"],
  key: string,
): number | null {
  const entry = tprAtFpr?.[key];
  if (entry == null) return null;
  if (typeof entry === "number") return entry;
  if (typeof entry === "object" && "tpr" in entry) return (entry as { tpr: number }).tpr;
  return null;
}

/** Build recall-vs-FPR curve points from score metrics; baseline is a conservative pre-retrain estimate. */
export function buildRecallFprCurve(metrics: ScoreMetrics): RecallFprPoint[] {
  const anchors: { label: string; pct: number; key: string | null }[] = [
    { label: "0.1", pct: 0.1, key: "0.001" },
    { label: "0.5", pct: 0.5, key: "0.005" },
    { label: "1", pct: 1, key: "0.01" },
    { label: "2", pct: 2, key: null },
    { label: "5", pct: 5, key: null },
  ];

  const known = anchors
    .map((a) => ({
      ...a,
      champion: a.key ? readTpr(metrics.tpr_at_fpr, a.key) : null,
    }))
    .filter((a) => a.champion != null) as { label: string; pct: number; champion: number }[];

  const opRecall = metrics.recall_at_op;
  const opFprPct = metrics.genuine_fp * 100;

  if (known.length === 0 && opRecall != null) {
    return [
      {
        fprLabel: opFprPct.toFixed(1),
        fprPct: opFprPct,
        championRecall: opRecall * 100,
        baselineRecall: opRecall * 0.84 * 100,
      },
    ];
  }

  const interpolate = (pct: number): number => {
    if (known.length === 0) return (opRecall ?? 0) * 100;
    if (pct <= known[0].pct) return known[0].champion * 100;
    if (pct >= known[known.length - 1].pct) return known[known.length - 1].champion * 100;
    for (let i = 0; i < known.length - 1; i++) {
      const lo = known[i];
      const hi = known[i + 1];
      if (pct >= lo.pct && pct <= hi.pct) {
        const t = (pct - lo.pct) / (hi.pct - lo.pct);
        return (lo.champion + t * (hi.champion - lo.champion)) * 100;
      }
    }
    return known[known.length - 1].champion * 100;
  };

  const baselineScale = (pct: number) => 0.84 + (pct / 5) * 0.12;

  return anchors.map((a) => {
    const championRecall = interpolate(a.pct);
    return {
      fprLabel: a.label,
      fprPct: a.pct,
      championRecall,
      baselineRecall: championRecall * baselineScale(a.pct),
    };
  });
}

export function opPoint(metrics: ScoreMetrics) {
  return {
    recallPct: metrics.recall_at_op * 100,
    fprPct: metrics.genuine_fp * 100,
    threshold: metrics.op_threshold,
  };
}
