import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

interface LatestRunContextValue {
  runId: string | null;
  setRunId: (id: string | null) => void;
  lastScore: import("@/lib/api-types").ScoreResponse | null;
  setLastScore: (score: import("@/lib/api-types").ScoreResponse | null) => void;
}

const LatestRunContext = createContext<LatestRunContextValue | null>(null);

export function LatestRunProvider({ children }: { children: ReactNode }) {
  const [runId, setRunId] = useState<string | null>(null);
  const [lastScore, setLastScore] = useState<import("@/lib/api-types").ScoreResponse | null>(null);
  const value = useMemo(
    () => ({ runId, setRunId, lastScore, setLastScore }),
    [runId, lastScore],
  );
  return <LatestRunContext.Provider value={value}>{children}</LatestRunContext.Provider>;
}

export function useLatestRun() {
  const ctx = useContext(LatestRunContext);
  if (!ctx) throw new Error("useLatestRun must be used within LatestRunProvider");
  return ctx;
}
