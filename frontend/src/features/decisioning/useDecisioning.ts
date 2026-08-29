import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { FitResponse, ScoreResponse } from "@/lib/api-types";
import { useLatestRun } from "@/lib/latest-run-context";

export function useDecisioning() {
  const qc = useQueryClient();
  const { runId, setLastScore } = useLatestRun();

  const fit = useMutation({
    mutationFn: () => {
      if (!runId) throw new Error("No run_id — run population first");
      return api.post<FitResponse>("/defend/fit", { run_id: runId, world_seed: 42 });
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["defend-model"] });
    },
  });

  const score = useMutation({
    mutationFn: () => {
      if (!runId) throw new Error("No run_id — run population first");
      return api.post<ScoreResponse>("/defend/score", { run_id: runId, model_run_id: runId });
    },
    onSuccess: (data) => {
      setLastScore(data);
      void qc.invalidateQueries({ queryKey: ["defend-score"] });
      void qc.invalidateQueries({ queryKey: ["coverage-map"] });
    },
  });

  return { fit, score, runId, scoreData: score.data ?? null };
}
