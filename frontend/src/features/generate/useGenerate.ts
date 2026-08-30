import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { GenerateRunResponse } from "@/lib/api-types";
import { setGenerateRun } from "@/lib/session-store";

const DEMO_SCALE = { n_customers: 200, n_merchants: 40, sim_days: 14 };
const FULL_SCALE = { n_customers: 2400, n_merchants: 120, sim_days: 30 };

export function useGenerate() {
  const eligible = useQuery({
    queryKey: ["generate-eligible"],
    queryFn: () => api.get<{ count: number; items: unknown[] }>("/generate/eligible"),
  });

  const simulate = useMutation({
    mutationFn: (scale: "demo" | "full") =>
      api.post<GenerateRunResponse>("/generate/population", {
        world_seed: 42,
        ...(scale === "demo" ? DEMO_SCALE : FULL_SCALE),
      }),
    onSuccess: (data, scale) => {
      setGenerateRun(
        data.run_id,
        data.world_seed ?? 42,
        scale,
        data.fidelity?.pass ?? false,
        data.event_count ?? 0,
        data.counts_by_label_family ?? null,
        data.fidelity?.mule_fan_in_median ?? null,
      );
    },
  });

  const canary = useMutation({
    mutationFn: () =>
      api.post<GenerateRunResponse>("/generate/canary", {
        campaign_id: "fincen-typology",
        world_seed: 42,
        n_customers: 120,
        n_merchants: 20,
        sim_days: 14,
      }),
    onSuccess: (data) => {
      setGenerateRun(
        data.run_id,
        data.world_seed ?? 42,
        "demo",
        data.fidelity?.pass ?? false,
        data.event_count ?? 0,
        data.counts_by_label_family ?? null,
        data.fidelity?.mule_fan_in_median ?? null,
      );
    },
  });

  return { eligible, simulate, canary, DEMO_SCALE };
}
