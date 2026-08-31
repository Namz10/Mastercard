import type { GenerateRunResponse } from "@/lib/api-types";

export function normalizeGenerateResult(raw: Record<string, unknown>): GenerateRunResponse {
  const fidelity = raw.fidelity as GenerateRunResponse["fidelity"] | undefined;
  if (fidelity && raw.parquet_path !== undefined) {
    return raw as unknown as GenerateRunResponse;
  }
  return {
    run_id: String(raw.run_id ?? "demo-pop-v1"),
    world_seed: Number(raw.world_seed ?? raw.seed ?? 42),
    mode: (raw.mode as "demo" | "full") ?? "full",
    parquet_path: String(raw.parquet_path ?? "recorded"),
    sidecar_path: String(raw.sidecar_path ?? "recorded"),
    event_count: Number(raw.event_count ?? 0),
    counts_by_label_family: (raw.counts_by_label_family ?? raw.family_counts ?? {}) as Record<string, number>,
    fidelity: {
      pass: Boolean(fidelity?.pass ?? raw.fidelity_pass),
      reasons: (fidelity?.reasons ?? raw.fidelity_reasons) as string[] | undefined,
      mule_fan_in_median: Number(fidelity?.mule_fan_in_median ?? raw.mule_fan_in ?? 0) || undefined,
    },
  };
}
