import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { FitResponse, LoopMResponse, ScoreMetrics, ScoreResponse } from "@/lib/api-types";
import { missFamilyToTechnique, worstApFamily } from "@/lib/format";
import {
  setDefendScore,
  setRetrainResult,
  setSourceChip,
  useSessionSnapshot,
} from "@/lib/session-store";
import { COPY } from "@/lib/copy";
import { useRecordedPacks } from "@/hooks/useRecordedPacks";

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
  const { loadScore, loadLoop } = useRecordedPacks();
  const booted = useRef(false);
  const scoreLoadInflight = useRef(false);
  const [retrainError, setRetrainError] = useState<string | null>(null);
  const [retrainLive, setRetrainLive] = useState(false);

  const score = useMutation({
    mutationFn: async () => {
      const runId = session.generate.runId;
      if (!runId) throw new Error("no run");
      const fit = await api.post<FitResponse>("/defend/fit", { run_id: runId, world_seed: session.generate.seed ?? 42 });
      const modelRunId = fit.model_run_id;
      return api.post<ScoreResponse>("/defend/score", { run_id: runId, model_run_id: modelRunId });
    },
    onSuccess: (data) => {
      setDefendScore(data, data.model_run_id);
      setSourceChip("live");
    },
  });

  const retrain = useMutation({
    mutationFn: async () => {
      const runId = session.generate.runId;
      const current = session.defend.score;
      if (!runId || !current) throw new Error("no generate run");
      const missFamily = worstApFamily(current.metrics.ap_by_family);
      return api.post<LoopMResponse>("/defend/loop-m", {
        run_id: runId,
        miss_family: missFamily,
        train_seed: 42,
        gtest_seed: 48,
        family_chosen_from_slice: "gdev44",
        n_customers: session.generate.scale === "demo" ? 200 : undefined,
        n_merchants: session.generate.scale === "demo" ? 40 : undefined,
        sim_days: session.generate.scale === "demo" ? 14 : undefined,
      });
    },
    onSuccess: (data) => {
      const after: ScoreResponse = {
        run_id: data.run_id,
        model_run_id: data.model_run_id_after,
        metrics: data.metrics.gtest_after,
        action_histogram: session.defend.score?.action_histogram ?? {},
        split: "gtest",
        recipe_hash: data.metrics.gtest_after.recipe_hash,
        model_freeze_id: data.metrics.gtest_after.model_freeze_id,
      };
      setRetrainResult(
        after,
        data.model_run_id_after,
        missFamilyToTechnique(data.miss_family),
        data as unknown as Record<string, unknown>,
      );
      setRetrainLive(true);
      setRetrainError(null);
    },
  });

  const loadFrozenOrLive = async (preferLive: boolean) => {
    if (scoreLoadInflight.current) return;
    scoreLoadInflight.current = true;
    try {
      if (preferLive && session.generate.runId) {
        try {
          await score.mutateAsync();
          return;
        } catch {
          /* fall through to frozen champion pack */
        }
      }
      try {
        await loadScore();
      } catch {
        if (!session.defend.score) setSourceChip("recorded", COPY.defend.frozen);
      }
    } finally {
      scoreLoadInflight.current = false;
    }
  };

  useEffect(() => {
    if (booted.current) return;
    booted.current = true;
    const existing = session.defend.score;
    if (existing && !scoreLooksBroken(existing.metrics)) return;
    void loadFrozenOrLive(Boolean(session.generate.runId));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const prevRunId = useRef(session.generate.runId);
  useEffect(() => {
    const runId = session.generate.runId;
    if (runId === prevRunId.current) return;
    prevRunId.current = runId;
    if (!runId) return;
    void loadFrozenOrLive(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session.generate.runId]);

  useEffect(() => {
    const existing = session.defend.score;
    if (!existing || !scoreLooksBroken(existing.metrics)) return;
    void loadFrozenOrLive(Boolean(session.generate.runId));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session.defend.score]);

  const canRetrain = Boolean(session.generate.runId && session.defend.score);

  const overlayRetrain = async () => {
    if (!canRetrain) return;
    setRetrainError(null);
    try {
      await retrain.mutateAsync();
    } catch {
      setRetrainLive(false);
      setRetrainError(COPY.defend.retrainFail);
      setSourceChip("frozen", COPY.defend.retrainFail);
      try {
        await loadLoop();
      } catch {
        /* recorded overlay optional */
      }
    }
  };

  return { session, score, retrain, overlayRetrain, loadScore, retrainError, retrainLive, canRetrain };
}
