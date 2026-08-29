import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { HitlDecisionResponse, HitlQueueResponse, IdentifyRunResponse } from "@/lib/api-types";

export function useHitlQueue(enabled = true) {
  return useQuery({
    queryKey: ["identify-hitl"],
    queryFn: () => api.get<HitlQueueResponse>("/identify/hitl"),
    enabled,
  });
}

export function useIdentifyMutations() {
  const qc = useQueryClient();

  const runResearch = useMutation({
    mutationFn: (topic: string) => api.post<IdentifyRunResponse>("/identify/run", { topic }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["identify-hitl"] });
    },
  });

  const approve = useMutation({
    mutationFn: (vectorId: string) =>
      api.post<HitlDecisionResponse>(`/identify/approve/${vectorId}`, { action: "approve" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["identify-hitl"] });
      void qc.invalidateQueries({ queryKey: ["threat-map"] });
      void qc.invalidateQueries({ queryKey: ["coverage-map"] });
    },
  });

  const reject = useMutation({
    mutationFn: (vectorId: string) => api.post<HitlDecisionResponse>(`/identify/reject/${vectorId}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["identify-hitl"] });
    },
  });

  const rejectUnsafe = useMutation({
    mutationFn: (vectorId: string) =>
      api.post<HitlDecisionResponse>(`/identify/reject-unsafe/${vectorId}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["identify-hitl"] });
    },
  });

  return { runResearch, approve, reject, rejectUnsafe };
}
