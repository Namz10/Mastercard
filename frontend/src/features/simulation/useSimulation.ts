import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { GenerateRunResponse } from "@/lib/api-types";
import { useLatestRun } from "@/lib/latest-run-context";

export function useSimulation() {
  const qc = useQueryClient();
  const { setRunId } = useLatestRun();

  const invalidate = () => {
    void qc.invalidateQueries({ queryKey: ["generate-latest"] });
    void qc.invalidateQueries({ queryKey: ["coverage-map"] });
    void qc.invalidateQueries({ queryKey: ["alerts"] });
  };

  const population = useMutation({
    mutationFn: () =>
      api.post<GenerateRunResponse>("/generate/population", {
        world_seed: 42,
        n_customers: 2400,
        n_merchants: 120,
        sim_days: 30,
      }),
    onSuccess: (data) => {
      setRunId(data.run_id);
      // Persist full generate run response
      try {
        localStorage.setItem(`generate_${data.run_id}`, JSON.stringify(data));
      } catch (e) {
        console.error("Failed to store generate result", e);
      }
      invalidate();
    },
  });

  const canary = useMutation({
    mutationFn: (campaign_id: string) =>
      api.post<GenerateRunResponse>("/generate/canary", {
        campaign_id,
        world_seed: 42,
        n_customers: 120,
        n_merchants: 20,
        sim_days: 30,
      }),
    onSuccess: (data) => {
      setRunId(data.run_id);
      // Persist full generate canary response
      try {
        localStorage.setItem(`generate_${data.run_id}`, JSON.stringify(data));
      } catch (e) {
        console.error("Failed to store generate result", e);
      }
      invalidate();
    },
  });

  const latest = population.data ?? canary.data ?? null;

  return { population, canary, latest };
}
