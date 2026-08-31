import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { ScoreMetrics } from "@/lib/api-types";
import { useSessionSnapshot } from "@/lib/session-store";
import { useDefendLoopJob, useDefendScoreJob, useDefendTuneJob } from "@/lib/defend-job";

function readTprValues(tprAtFpr: ScoreMetrics["tpr_at_fpr"]): number[] {
  if (!tprAtFpr) return [];
  return Object.values(tprAtFpr).map((entry) => {
    if (typeof entry === "number") return entry;
    if (entry && typeof entry === "object" && "tpr" in entry) return (entry as { tpr: number }).tpr;
    return 0;
  });
}

/** Photography-day and other legacy packs show ~8–10% FPR or a flat curve — not booth champion. */
export function scoreLooksBroken(metrics: ScoreMetrics): boolean {
  if (metrics.genuine_fp > 0.01) return true;
  const recalls = readTprValues(metrics.tpr_at_fpr);
  if (recalls.length >= 2 && Math.max(...recalls) - Math.min(...recalls) < 0.001) return true;
  if (metrics.recall_at_op >= 0.995 && metrics.genuine_fp > 0.005) return true;
  return false;
}

export function useDefend() {
  const session = useSessionSnapshot();
  const score = useDefendScoreJob();
  const retrain = useDefendLoopJob();
  const tune = useDefendTuneJob();

  return { session, score, retrain, tune };
}

export function useGenerateEligible() {
  return useQuery({
    queryKey: ["generate-eligible"],
    queryFn: () => api.get<{ count: number; items: unknown[] }>("/generate/eligible"),
  });
}
