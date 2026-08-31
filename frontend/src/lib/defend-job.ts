import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { LoopMResponse, ScoreResponse } from "@/lib/api-types";
import { missFamilyToTechnique, worstApFamily } from "@/lib/format";
import { useJobStream } from "@/hooks/useJobStream";
import {
  getSession,
  setDefendScore,
  setRetrainResult,
  setSourceChip,
  setTuneResult,
} from "@/lib/session-store";

const SCORE_KEY = ["defend-score-job"] as const;
const LOOP_KEY = ["defend-loop-job"] as const;
const TUNE_KEY = ["defend-tune-job"] as const;

let scoreInflight: Promise<ScoreResponse> | null = null;
let scoreInflightRunId: string | null = null;

async function runFitScoreStream(
  runId: string,
  worldSeed: number,
  run: (path: string, body: unknown) => Promise<ScoreResponse>,
): Promise<ScoreResponse> {
  return run("/defend/fit/stream", { run_id: runId, world_seed: worldSeed });
}

export function ensureDefendScore(
  runId: string,
  worldSeed: number,
  run: (path: string, body: unknown) => Promise<ScoreResponse>,
): Promise<ScoreResponse> {
  if (scoreInflight && scoreInflightRunId === runId) return scoreInflight;
  scoreInflightRunId = runId;
  scoreInflight = runFitScoreStream(runId, worldSeed, run)
    .then((data) => {
      setDefendScore(data, data.model_run_id);
      const session = getSession();
      if (!session.ui.recordedReason) setSourceChip("live");
      return data;
    })
    .finally(() => {
      scoreInflight = null;
      scoreInflightRunId = null;
    });
  return scoreInflight;
}

export function useDefendScoreJob() {
  const qc = useQueryClient();
  const stream = useJobStream<ScoreResponse>();

  const mutation = useMutation({
    mutationKey: SCORE_KEY,
    mutationFn: async () => {
      const session = getSession();
      const runId = session.generate.runId;
      if (!runId) throw new Error("no run");
      return ensureDefendScore(runId, session.generate.seed ?? 42, stream.run);
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: SCORE_KEY });
    },
  });

  return { ...mutation, stream };
}

export function useDefendLoopJob() {
  const stream = useJobStream<LoopMResponse>();

  const mutation = useMutation({
    mutationKey: LOOP_KEY,
    mutationFn: async () => {
      const session = getSession();
      const runId = session.generate.runId;
      const current = session.defend.score;
      if (!runId || !current) throw new Error("no generate run");
      const missFamily = worstApFamily(current.metrics.ap_by_family);
      return stream.run("/defend/loop-m/stream", {
        run_id: runId,
        miss_family: missFamily,
        train_seed: 42,
        gtest_seed: 48,
        family_chosen_from_slice: "gdev44",
      });
    },
    onSuccess: (data) => {
      const session = getSession();
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
      if (!session.ui.recordedReason) setSourceChip("live");
    },
  });

  return { ...mutation, stream };
}

export function useDefendTuneJob() {
  const stream = useJobStream<Record<string, unknown>>();

  const mutation = useMutation({
    mutationKey: TUNE_KEY,
    mutationFn: async () => {
      const session = getSession();
      const runId = session.generate.runId;
      if (!runId) throw new Error("no run");
      const destRunId = `${runId}-stage2`;
      const tuneResult = await stream.run("/defend/tune/stream", {
        run_id: runId,
        world_seed: session.generate.seed ?? 42,
        dest_run_id: destRunId,
      });
      const tunedScore = await api.post<ScoreResponse>("/defend/score", {
        run_id: runId,
        model_run_id: destRunId,
      });
      return { tuneResult, tunedScore, destRunId };
    },
    onSuccess: ({ tuneResult, tunedScore, destRunId }) => {
      const session = getSession();
      setTuneResult(tunedScore, destRunId, tuneResult);
      if (!session.ui.recordedReason) setSourceChip("live");
    },
  });

  return { ...mutation, stream };
}

export function resetDefendJobForTests() {
  scoreInflight = null;
  scoreInflightRunId = null;
}
