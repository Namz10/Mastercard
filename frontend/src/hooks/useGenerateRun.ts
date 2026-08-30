import { useEffect, useState } from "react";
import { useLatestRun } from "@/lib/latest-run-context";
import type { GenerateRunResponse } from "@/lib/api-types";

export function useGenerateRun() {
  const { runId } = useLatestRun();
  const [data, setData] = useState<GenerateRunResponse | null>(null);
  const [isLoading, setLoading] = useState(false);

  useEffect(() => {
    if (!runId) {
      setData(null);
      return;
    }
    const key = `generate_${runId}`;
    const raw = localStorage.getItem(key);
    if (raw) {
      try {
        setData(JSON.parse(raw) as GenerateRunResponse);
      } catch {
        setData(null);
      }
    } else {
      setData(null);
    }
  }, [runId]);

  return { data, isLoading };
}
