import { useMemo, type ReactNode } from "react";
import { useSessionSnapshot } from "@/lib/session-store";
import type { ScoreResponse } from "@/lib/api-types";

export function LatestRunProvider({ children }: { children: ReactNode }) {
  return children;
}

export function useLatestRun() {
  const session = useSessionSnapshot();
  return useMemo(
    () => ({
      runId: session.generate.runId,
      setRunId: (_id: string | null) => undefined,
      lastScore: session.defend.score,
      setLastScore: (_s: ScoreResponse | null) => undefined,
    }),
    [session],
  );
}
