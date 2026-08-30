import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError, api } from "@/lib/api-client";
import type { GenerateRunResponse } from "@/lib/api-types";
import { useLatestRun } from "@/lib/latest-run-context";

function persistRun(data: GenerateRunResponse, setRunId: (id: string | null) => void) {
  // Write storage BEFORE setRunId so useGenerateRun's effect can read it.
  try {
    localStorage.setItem(`generate_${data.run_id}`, JSON.stringify(data));
  } catch (e) {
    console.error("Failed to store generate result", e);
  }
  setRunId(data.run_id);
}

export function useSimulation(opts?: {
  onRunComplete?: (data: GenerateRunResponse) => void | Promise<void>;
}) {
  const qc = useQueryClient();
  const { setRunId } = useLatestRun();
  const onRunComplete = opts?.onRunComplete;

  const invalidate = () => {
    void qc.invalidateQueries({ queryKey: ["generate-latest"] });
    void qc.invalidateQueries({ queryKey: ["coverage-map"] });
    void qc.invalidateQueries({ queryKey: ["alerts"] });
  };

  const population = useMutation({
    mutationFn: () =>
      api.post<GenerateRunResponse>("/generate/population", {
        world_seed: 42,
        // Must clear fidelity gate (mule_fan_in_median > 5). n≈64 fails; n≈240 passes.
        n_customers: 240,
        n_merchants: 40,
        sim_days: 30,
        pin: true,
      }),
    onSuccess: async (data) => {
      persistRun(data, setRunId);
      invalidate();
      await onRunComplete?.(data);
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
    onSuccess: async (data) => {
      persistRun(data, setRunId);
      invalidate();
      await onRunComplete?.(data);
    },
  });

  const latest = population.data ?? canary.data ?? null;
  const pending = population.isPending || canary.isPending;
  const error =
    (population.error as Error | null) ?? (canary.error as Error | null) ?? null;
  const errorText = error
    ? error instanceof ApiError
      ? `Generate failed (${error.status}): ${error.message.slice(0, 200)}`
      : error.message
    : null;

  return { population, canary, latest, pending, errorText };
}
