import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { CoverageMapResponse, MergedTechnique, ThreatMapResponse } from "@/lib/api-types";
import { CATEGORY_LABELS, techniqueCategory } from "@/lib/format";

function mergeThreatData(
  coverage: CoverageMapResponse,
  threat: ThreatMapResponse,
): MergedTechnique[] {
  const threatById = new Map<string, ThreatMapResponse["categories"][string][number]>();
  for (const groups of Object.values(threat.categories)) {
    for (const group of groups) {
      threatById.set(group.technique_id, group);
    }
  }

  return coverage.cells.map((cell) => {
    const group = threatById.get(cell.technique_id);
    const primaryChip = group?.chips[0];
    return {
      technique_id: cell.technique_id,
      name: cell.name ?? group?.name ?? cell.technique_id,
      coverage_status: cell.coverage_status,
      vector_id: cell.vector_id,
      generate_mode: cell.generate_mode ?? group?.generate_mode ?? null,
      confidence_level: group?.confidence_level ?? primaryChip?.confidence_level ?? null,
      source_tier: primaryChip?.source_tier ?? group?.source_tier ?? null,
      live_rule_ids: cell.live_rule_ids,
      named_gap_reason: cell.named_gap_reason,
      features_expected: cell.features_expected,
      scout_topic_hint: cell.scout_topic_hint,
      variants: group?.variants ?? 0,
      chips: group?.chips ?? [],
      category: primaryChip?.category ?? techniqueCategory(cell.technique_id),
    };
  });
}

export function useThreatMap() {
  const coverageQuery = useQuery({
    queryKey: ["coverage-map"],
    queryFn: () => api.get<CoverageMapResponse>("/defend/coverage-map"),
  });

  const threatQuery = useQuery({
    queryKey: ["threat-map"],
    queryFn: () => api.get<ThreatMapResponse>("/catalog/threat-map"),
  });

  const techniques =
    coverageQuery.data && threatQuery.data
      ? mergeThreatData(coverageQuery.data, threatQuery.data)
      : [];

  const byCategory = techniques.reduce<Record<number, MergedTechnique[]>>((acc, t) => {
    acc[t.category] = acc[t.category] ?? [];
    acc[t.category].push(t);
    return acc;
  }, {});

  return {
    techniques,
    byCategory,
    categoryLabels: CATEGORY_LABELS,
    isLoading: coverageQuery.isLoading || threatQuery.isLoading,
    isError: coverageQuery.isError || threatQuery.isError,
    error: coverageQuery.error ?? threatQuery.error,
    refetch: () => {
      void coverageQuery.refetch();
      void threatQuery.refetch();
    },
  };
}
