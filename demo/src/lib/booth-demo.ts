import type { NavigateFunction } from "react-router-dom";
import { postSse } from "@/lib/api-client";
import type { LoopMResponse, ScoreResponse } from "@/lib/api-types";
import { POPULATION_SCALE } from "@/lib/generate-job";
import { normalizeGenerateResult } from "@/lib/generate-job-normalize";
import {
  acceptCatalogSeed,
  approveAttack,
  setDefendScore,
  setGenerateRun,
  setRetrainResult,
  setSourceChip,
} from "@/lib/session-store";
import { missFamilyToTechnique } from "@/lib/format";

export interface BoothDemoDeps {
  navigate: NavigateFunction;
}

/** Full booth walk: identify → generate → defend → loop M → hyperparameters */
export async function runBoothDemo({ navigate }: BoothDemoDeps): Promise<void> {
  acceptCatalogSeed();
  setSourceChip("recorded", "Play full demo");

  navigate("/identify/discover");
  await postSse("/identify/run/stream", { topic: "UPI fraud" }, () => {});

  navigate("/identify/review");
  approveAttack({
    id: "hitl-t11",
    techniqueId: "T11",
    name: "Identity farming burst",
  });

  navigate("/generate");
  let generateRaw: Record<string, unknown> | null = null;
  await postSse("/generate/population/stream", {
    world_seed: 42,
    pin: true,
    ...POPULATION_SCALE,
  }, (ev) => {
    if (ev.result) generateRaw = ev.result;
  });
  if (generateRaw) {
    const data = normalizeGenerateResult(generateRaw);
    setGenerateRun(
      data.run_id,
      data.world_seed ?? 42,
      "full",
      data.fidelity?.pass ?? false,
      data.event_count ?? 0,
      data.counts_by_label_family ?? null,
      data.fidelity?.mule_fan_in_median ?? null,
      data.fidelity?.reasons ?? null,
    );
  }

  navigate("/defend/detection");
  let scoreRaw: Record<string, unknown> | null = null;
  await postSse("/defend/fit/stream", { run_id: "demo-pop-v1", world_seed: 42 }, (ev) => {
    if (ev.result) scoreRaw = ev.result;
  });
  if (scoreRaw) {
    const score = scoreRaw as ScoreResponse;
    setDefendScore(score, score.model_run_id);
  }

  navigate("/defend/interventions");
  await sleep(800);

  navigate("/defend/feedback");
  let loopRaw: Record<string, unknown> | null = null;
  await postSse("/defend/loop-m/stream", {
    run_id: "demo-pop-v1",
    miss_family: "identity_burst",
    train_seed: 46,
    gtest_seed: 48,
  }, (ev) => {
    if (ev.result) loopRaw = ev.result;
  });
  if (loopRaw) {
    const data = loopRaw as LoopMResponse;
    const gBefore = data.metrics.gtest_before;
    const gAfter = data.metrics.gtest_after;
    const before: ScoreResponse = {
      run_id: data.gtest_run_id ?? data.run_id,
      model_run_id: data.model_run_id_before,
      metrics: gBefore,
      action_histogram: {},
      split: "gtest",
      recipe_hash: gBefore.recipe_hash,
      model_freeze_id: gBefore.model_freeze_id,
    };
    const after: ScoreResponse = {
      run_id: data.gtest_run_id ?? data.run_id,
      model_run_id: data.model_run_id_after,
      metrics: gAfter,
      action_histogram: {},
      split: "gtest",
      recipe_hash: gAfter.recipe_hash,
      model_freeze_id: gAfter.model_freeze_id,
    };
    setRetrainResult(
      after,
      data.model_run_id_after,
      missFamilyToTechnique(data.miss_family),
      data as unknown as Record<string, unknown>,
      before,
    );
  }

  navigate("/defend/hyperparameters");
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

export const BOOTH_DEMO_LABEL = "Run booth demo";
