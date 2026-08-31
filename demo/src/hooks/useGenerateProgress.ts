import { useMemo } from "react";
import type { OpsTapeLine } from "@/lib/ops-tape-types";

export interface GenerateProgress {
  eventCount: number | null;
  customersDone: number | null;
  nCustomers: number | null;
  lastBody: string | null;
}

/** Latest counters from generate SSE artifacts on the job thread. */
export function useGenerateProgress(lines: OpsTapeLine[]): GenerateProgress {
  return useMemo(() => {
    let eventCount: number | null = null;
    let customersDone: number | null = null;
    let nCustomers: number | null = null;
    let lastBody: string | null = null;

    for (const line of lines) {
      lastBody = line.body;
      const art = line.artifacts;
      if (!art) continue;
      if (typeof art.event_count === "number") eventCount = art.event_count;
      if (typeof art.customers_done === "number") customersDone = art.customers_done;
      if (typeof art.n_customers === "number") nCustomers = art.n_customers;
    }

    return { eventCount, customersDone, nCustomers, lastBody };
  }, [lines]);
}
