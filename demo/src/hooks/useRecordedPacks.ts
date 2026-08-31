import { useCallback } from "react";
import { api } from "@/lib/api-client";
import { COPY } from "@/lib/copy";
import { setDefendScore, setSession, setSourceChip } from "@/lib/session-store";
import type { ScoreResponse } from "@/lib/api-types";

export function useRecordedPacks() {
  const loadScore = useCallback(async () => {
    const score = await api.get<ScoreResponse>("/demo/recorded/score");
    setDefendScore(score, score.model_run_id);
    setSourceChip("recorded", COPY.defend.frozen);
    return score;
  }, []);

  const loadLoop = useCallback(async () => {
    const loop = await api.get<Record<string, unknown>>("/demo/recorded/loop");
    setSession((prev) => ({
      ...prev,
      defend: { ...prev.defend, loopResult: loop },
    }));
    return loop;
  }, []);

  const loadIdentify = useCallback(async () => {
    const pack = await api.get<{ events: unknown[]; run_id: string }>("/demo/recorded/identify");
    setSourceChip("recorded", COPY.identify.fallback);
    return pack;
  }, []);

  return { loadScore, loadLoop, loadIdentify };
}
