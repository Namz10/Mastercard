import { useEffect, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { FitResponse, LoopMResponse, ScoreResponse } from "@/lib/api-types";
import { missFamilyToTechnique, worstApFamily } from "@/lib/format";
import {
  setDefendScore,
  setRetrainResult,
  setSourceChip,
  useSessionSnapshot,
} from "@/lib/session-store";
import { COPY } from "@/lib/copy";
import { useRecordedPacks } from "@/hooks/useRecordedPacks";

export function useDefend() {
  const session = useSessionSnapshot();
  const { loadScore, loadLoop } = useRecordedPacks();
  const booted = useRef(false);

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
    },
  });

  const retrain = useMutation({
    mutationFn: async () => {
      const runId = session.generate.runId;
      const current = session.defend.score;
      if (!runId || !current) throw new Error("no score");
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
    },
  });

  useEffect(() => {
    if (booted.current) return;
    booted.current = true;
    if (session.defend.score) return;
    void (async () => {
      try {
        await loadScore();
      } catch {
        if (session.generate.runId) {
          try {
            await score.mutateAsync();
          } catch {
            setSourceChip("frozen", COPY.defend.frozen);
          }
        }
      }
    })();
    // boot once
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const overlayRetrain = async () => {
    try {
      await retrain.mutateAsync();
    } catch {
      const loop = await loadLoop();
      const family = typeof loop.miss_family === "string" ? loop.miss_family : "app_fraud";
      if (session.defend.score) {
        setRetrainResult(
          session.defend.score,
          session.defend.modelRunId ?? session.defend.score.model_run_id,
          missFamilyToTechnique(family),
          loop,
        );
      }
      setSourceChip("frozen", COPY.defend.updated);
    }
  };

  return { session, score, retrain, overlayRetrain, loadScore };
}
