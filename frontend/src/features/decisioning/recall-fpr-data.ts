import type { ScoreMetrics } from "@/lib/api-types";

export interface RecallFprPoint {
  fprLabel: string;
  fprPct: number;
  recall: number;
  beforeRecall?: number;
}

/** Booth anchors — genuine FPR caps shown on the Defend curve. */
const ANCHOR_FPR: { label: string; pct: number; fpr: number }[] = [
  { label: "0.05", pct: 0.05, fpr: 0.0005 },
  { label: "0.1", pct: 0.1, fpr: 0.001 },
  { label: "0.5", pct: 0.5, fpr: 0.005 },
  { label: "1", pct: 1, fpr: 0.01 },
];

interface CurvePoint {
  fpr: number;
  recall: number;
}

function extractCurvePoints(tprAtFpr: ScoreMetrics["tpr_at_fpr"]): CurvePoint[] {
  const pts: CurvePoint[] = [];
  for (const [key, entry] of Object.entries(tprAtFpr ?? {})) {
    let recall: number | null = null;
    let fpr: number | null = null;
    if (typeof entry === "number") {
      recall = entry;
      fpr = Number.parseFloat(key);
    } else if (entry && typeof entry === "object") {
      if ("tpr" in entry) recall = (entry as { tpr: number }).tpr;
      if ("fpr_target" in entry) fpr = (entry as { fpr_target: number }).fpr_target;
      else fpr = Number.parseFloat(key);
    }
    if (recall != null && fpr != null && Number.isFinite(fpr) && Number.isFinite(recall)) {
      pts.push({ fpr, recall });
    }
  }
  return pts.sort((a, b) => a.fpr - b.fpr);
}

function interpolateRecall(pts: CurvePoint[], targetFpr: number, fallbackRecall: number): number {
  if (pts.length === 0) return fallbackRecall * 100;
  if (targetFpr <= pts[0].fpr) return pts[0].recall * 100;
  if (targetFpr >= pts[pts.length - 1].fpr) return pts[pts.length - 1].recall * 100;
  for (let i = 0; i < pts.length - 1; i++) {
    const lo = pts[i];
    const hi = pts[i + 1];
    if (targetFpr >= lo.fpr && targetFpr <= hi.fpr) {
      const t = (targetFpr - lo.fpr) / (hi.fpr - lo.fpr);
      return (lo.recall + t * (hi.recall - lo.recall)) * 100;
    }
  }
  return pts[pts.length - 1].recall * 100;
}

function pointsFrom(metrics: ScoreMetrics): { label: string; pct: number; recall: number }[] {
  const curve = extractCurvePoints(metrics.tpr_at_fpr);
  const fallback = metrics.recall_at_op;

  if (curve.length === 0 && fallback != null) {
    const opFprPct = Math.max(0.02, metrics.genuine_fp * 100);
    return [{ label: opFprPct.toFixed(2), pct: opFprPct, recall: fallback * 100 }];
  }

  return ANCHOR_FPR.map((a) => ({
    label: a.label,
    pct: a.pct,
    recall: interpolateRecall(curve, a.fpr, fallback),
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

/** Zoom Y-axis to the curve so 98–99% recall is not visually flat. */
export function recallYDomain(points: RecallFprPoint[]): [number, number] {
  const recalls = points.flatMap((p) =>
    [p.recall, p.beforeRecall].filter((v): v is number => v != null),
  );
  if (recalls.length === 0) return [95, 100];
  const min = Math.min(...recalls);
  const max = Math.max(...recalls);
  const span = Math.max(max - min, 0.5);
  const pad = Math.max(0.25, span * 0.12);
  const lo = Math.floor((min - pad) * 10) / 10;
  const hi = Math.ceil((max + pad) * 10) / 10;
  return [lo, Math.min(100, hi)];
}

export function opPoint(metrics: ScoreMetrics) {
  return {
    recallPct: metrics.recall_at_op * 100,
    fprPct: metrics.genuine_fp * 100,
    threshold: metrics.op_threshold,
  };
}
