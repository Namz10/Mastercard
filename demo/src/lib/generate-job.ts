import { useMutation } from "@tanstack/react-query";
import type { GenerateRunResponse } from "@/lib/api-types";
import { normalizeGenerateResult } from "@/lib/generate-job-normalize";
import { setGenerateRun } from "@/lib/session-store";
import { useJobStream } from "@/hooks/useJobStream";

/** Full population — runner defaults (2400 × 120 × 90d). */
export const POPULATION_SCALE = { n_customers: 2400, n_merchants: 120, sim_days: 90 };

let simulateInflight: Promise<GenerateRunResponse> | null = null;

async function runSimulateStream(
  run: (path: string, body: unknown) => Promise<GenerateRunResponse>,
): Promise<GenerateRunResponse> {
  const raw = await run("/generate/population/stream", {
    world_seed: 42,
    pin: true,
    ...POPULATION_SCALE,
  });
  return normalizeGenerateResult(raw as unknown as Record<string, unknown>);
}

export function ensureSimulate(
  run: (path: string, body: unknown) => Promise<GenerateRunResponse>,
): Promise<GenerateRunResponse> {
  if (simulateInflight) return simulateInflight;
  simulateInflight = runSimulateStream(run)
    .then((data) => {
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
      return data;
    })
    .finally(() => {
      simulateInflight = null;
    });
  return simulateInflight;
}

export function useGenerateJob() {
  const stream = useJobStream<GenerateRunResponse>();

  const simulate = useMutation({
    mutationKey: ["generate-simulate"],
    mutationFn: () => ensureSimulate(stream.run),
  });

  return { simulate, stream, POPULATION_SCALE };
}

export function resetGenerateJobForTests() {
  simulateInflight = null;
}
