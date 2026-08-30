import { createContext, useContext, useMemo, useState, useEffect, type ReactNode } from "react";

interface LatestRunContextValue {
  runId: string | null;
  setRunId: (id: string | null) => void;
  lastScore: import("@/lib/api-types").ScoreResponse | null;
  setLastScore: (score: import("@/lib/api-types").ScoreResponse | null) => void;
}

const LatestRunContext = createContext<LatestRunContextValue | null>(null);

export function LatestRunProvider({ children }: { children: ReactNode }) {
  const [runId, setRunIdState] = useState<string | null>(null);
  const [lastScore, setLastScoreState] = useState<import("@/lib/api-types").ScoreResponse | null>(null);

  // Initialise from localStorage on mount (client‑side only)
  useEffect(() => {
    if (typeof window === "undefined") return;
    const storedRunId = localStorage.getItem("runId");
    if (storedRunId) setRunIdState(storedRunId);
    const storedScore = localStorage.getItem("lastScore");
    if (storedScore) {
      try {
        setLastScoreState(JSON.parse(storedScore) as import("@/lib/api-types").ScoreResponse);
      } catch {}
    }
  }, []);

  // Wrapper setters that also sync to localStorage
  const setRunId = (id: string | null) => {
    setRunIdState(id);
    if (typeof window !== "undefined") {
      if (id) localStorage.setItem("runId", id);
      else localStorage.removeItem("runId");
    }
  };

  const setLastScore = (score: import("@/lib/api-types").ScoreResponse | null) => {
    setLastScoreState(score);
    if (typeof window !== "undefined") {
      if (score) localStorage.setItem("lastScore", JSON.stringify(score));
      else localStorage.removeItem("lastScore");
    }
  };

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
