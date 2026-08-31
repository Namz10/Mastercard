import { useCallback, useRef, useState } from "react";
import { postSse, type SseEvent } from "@/lib/api-client";
import { formatIstClock } from "@/lib/format";
import { mapJobCatalogLine, mergeJobLine } from "@/lib/job-catalog-map";
import type { OpsTapeLine } from "@/lib/ops-tape-types";

function toLine(ev: SseEvent, index: number): OpsTapeLine | null {
  if (!ev.verb || !ev.body) return null;
  const mapped = mapJobCatalogLine(ev.verb, ev.body);
  if (mapped.skip) return null;
  return {
    id: `${ev.t ?? 0}-${mapped.verb}-${index}`,
    t: ev.t ?? 0,
    verb: mapped.verb,
    body: mapped.body,
    status: ev.status === "progress" ? "active" : ev.status,
    clock: formatIstClock(),
    artifacts: ev.artifacts,
  };
}

export function useJobStream<T>() {
  const [lines, setLines] = useState<OpsTapeLine[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lineIndex = useRef(0);
  const abortRef = useRef<AbortController | null>(null);

  const appendEvent = useCallback((ev: SseEvent) => {
    const line = toLine(ev, lineIndex.current++);
    if (!line) return;
    setLines((prev) => {
      const marked = prev.map((l) => ({ ...l, status: "done" as const }));
      return mergeJobLine(marked, { ...line, status: "active" });
    });
  }, []);

  const run = useCallback(
    async (path: string, body: unknown): Promise<T> => {
      abortRef.current?.abort();
      const ac = new AbortController();
      abortRef.current = ac;
      setRunning(true);
      setLines([]);
      setError(null);
      lineIndex.current = 0;

      let result: T | null = null;
      try {
        await postSse(
          path,
          body,
          (ev) => {
            if (ev.status === "error") {
              setError(ev.reason ?? "Job failed");
              return;
            }
            if (ev.verb && ev.body) appendEvent(ev);
            if (ev.status === "done" && ev.result) {
              result = ev.result as T;
              if (ev.verb && ev.body) {
                setLines((prev) =>
                  prev.map((l, i) => (i === prev.length - 1 ? { ...l, status: "done" } : l)),
                );
              }
            }
          },
          ac.signal,
        );
        if (!result) throw new Error("Stream ended without result");
        return result;
      } catch (e) {
        if ((e as { name?: string }).name === "AbortError") throw e;
        const msg = e instanceof Error ? e.message : "Job failed";
        setError(msg);
        throw e;
      } finally {
        setRunning(false);
        abortRef.current = null;
      }
    },
    [appendEvent],
  );

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setLines([]);
    setRunning(false);
    setError(null);
    lineIndex.current = 0;
  }, []);

  return { lines, running, error, run, reset };
}
