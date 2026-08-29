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
  };

  const population = useMutation({
    mutationFn: () =>
      api.post<GenerateRunResponse>("/generate/population", {
        world_seed: 42,
        n_customers: 2400,
        n_merchants: 120,
        sim_days: 90,
        pin: true,
      }),
    onSuccess: (data) => {
      setRunId(data.run_id);
      invalidate();
    },
  });

  const canary = useMutation({
    mutationFn: () =>
      api.post<GenerateRunResponse>("/generate/canary", {
        campaign_id: "fincen-fin-2024-alert004",
        world_seed: 42,
        n_customers: 120,
        n_merchants: 20,
        sim_days: 90,
      }),
    onSuccess: (data) => {
      setRunId(data.run_id);
      invalidate();
    },
  });

  const latest = population.data ?? canary.data ?? null;

  return { population, canary, latest };
}
