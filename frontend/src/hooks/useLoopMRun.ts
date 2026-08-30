import { useEffect, useState } from "react";
import { useLatestRun } from "@/lib/latest-run-context";
import type { LoopMResponse } from "@/lib/api-types";

export function useLoopMRun() {
  const { runId } = useLatestRun();
  const [data, setData] = useState<LoopMResponse | null>(null);
  const [isLoading, setLoading] = useState(false);

  useEffect(() => {
    if (!runId) {
      setData(null);
      return;
    }
    setLoading(true);
    const key = `loopm_${runId}`;
    const raw = localStorage.getItem(key);
    if (raw) {
      try {
        setData(JSON.parse(raw) as LoopMResponse);
      } catch {
        setData(null);
      }
    } else {
      setData(null);
    }
    setLoading(false);
  }, [runId]);

  return { data, isLoading };
}
