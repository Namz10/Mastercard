import { useMemo } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { ScoreResponse } from "@/lib/api-types";
import { useLatestRun } from "@/lib/latest-run-context";
import { STORAGE_KEYS } from "@/lib/storage-keys";
import { usePersistedState } from "@/lib/usePersistedState";
import type { ArmsRaceResult } from "@/features/arms-race/useArmsRaceState";
import type { RetrainQueueItem } from "@/features/arms-race/retrain-types";
import type {
  CommandCenterBriefResponse,
  CommandCenterSnapshot,
} from "./command-types";

const THREAD_ID = "demo-1";
const POLL_MS = 15_000;

function readScore(raw: ScoreResponse | null): number | null {
  const v = raw?.metrics?.genuine_fp;
  return typeof v === "number" && !Number.isNaN(v) ? v : null;
}

function readApDelta(raw: ArmsRaceResult | null): number | null {
  const v = raw?.loopM?.comparison?.ap_delta;
  return typeof v === "number" && !Number.isNaN(v) ? v : null;
}

function mergeClientState(
  snap: CommandCenterSnapshot,
  opts: {
    score: ScoreResponse | null;
    armsRace: ArmsRaceResult | null;
    queue: RetrainQueueItem[];
    runId: string | null;
  },
): CommandCenterSnapshot {
  const next: CommandCenterSnapshot = structuredClone(snap);

  const genuineFpr = readScore(opts.score);
  if (genuineFpr != null) {
    next.kpis.genuine_fpr = genuineFpr;
    next.defend.metrics = { ...next.defend.metrics, genuine_fp: genuineFpr };
  }

  const apDelta = readApDelta(opts.armsRace);
  if (apDelta != null) {
    next.kpis.loop_m_ap_delta = apDelta;
    next.evolve.loop_m_last = {
      ...next.evolve.loop_m_last,
      run_id: opts.armsRace?.loopM?.run_id ?? next.evolve.loop_m_last?.run_id,
      ap_delta: apDelta,
      pass: opts.armsRace?.loopM?.metrics?.pass ?? next.evolve.loop_m_last?.pass,
      genuine_fp_ok:
        opts.armsRace?.loopM?.comparison?.genuine_fp_ok ?? next.evolve.loop_m_last?.genuine_fp_ok,
    };
    if (!next.evolve.generation) next.evolve.generation = 1;
  }

  next.evolve.retrain_queue = opts.queue;
  // Demo honesty — never claim catalog solved
  next.evolve.catalog_solved = false;
  next.ethics = {
    ...next.ethics,
    synthetic_only: true,
    catalog_solved: false,
    cat4_public_api: false,
    llm_not_detector: true,
  };

  if (opts.runId) {
    next.generate.last_run = {
      ...next.generate.last_run,
      run_id: next.generate.last_run?.run_id || opts.runId,
    };
  }

  return next;
}

export function useCommandCenter() {
  const { runId } = useLatestRun();
  const [score] = usePersistedState<ScoreResponse | null>(STORAGE_KEYS.decisioningScore, null);
  const [armsRace] = usePersistedState<ArmsRaceResult | null>(STORAGE_KEYS.armsRaceResult, null);
  const [queue] = usePersistedState<RetrainQueueItem[]>(STORAGE_KEYS.retrainQueue, []);

  const snapshotQuery = useQuery({
    queryKey: ["command-center", "snapshot", THREAD_ID],
    queryFn: () =>
      api.get<CommandCenterSnapshot>(`/command-center/snapshot?thread_id=${THREAD_ID}`),
    refetchInterval: POLL_MS,
  });

  const snapshot = useMemo(() => {
    if (!snapshotQuery.data) return null;
    return mergeClientState(snapshotQuery.data, { score, armsRace, queue, runId });
  }, [snapshotQuery.data, score, armsRace, queue, runId]);

  const brief = useMutation({
    mutationFn: () =>
      api.post<CommandCenterBriefResponse>("/command-center/brief", {
        thread_id: THREAD_ID,
        snapshot: snapshot ?? undefined,
      }),
  });

  return {
    snapshot,
    threadId: THREAD_ID,
    runId,
    queueLength: queue.length,
    isLoading: snapshotQuery.isLoading,
    isError: snapshotQuery.isError,
    error: snapshotQuery.error,
    refetch: snapshotQuery.refetch,
    dataUpdatedAt: snapshotQuery.dataUpdatedAt,
    brief,
  };
}
