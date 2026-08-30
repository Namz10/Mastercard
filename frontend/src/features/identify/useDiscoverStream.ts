import { useCallback, useEffect, useRef, useState } from "react";
import { postSse, type SseEvent } from "@/lib/api-client";
import { COPY } from "@/lib/copy";
import { setSession, setSourceChip } from "@/lib/session-store";

export interface LogLine {
  id: string;
  t: number;
  verb: string;
  body: string;
  status?: string;
  artifacts?: Record<string, unknown>;
}

export type IdentifyStage = "rest" | "scanning" | "review";

export function useDiscoverStream(onComplete?: () => void) {
  const [stage, setStage] = useState<IdentifyStage>("rest");
  const [lines, setLines] = useState<LogLine[]>([]);
  const [sources, setSources] = useState<string[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const [newCount, setNewCount] = useState(0);
  const followRef = useRef(true);
  const [follow, setFollow] = useState(true);
  const onCompleteRef = useRef(onComplete);

  useEffect(() => {
    followRef.current = follow;
  }, [follow]);
  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  const discover = useCallback(async (topic = "") => {
    if (abortRef.current) return;
    setRunning(true);
    setStage("scanning");
    setLines([]);
    setSources([]);
    setError(null);
    setNewCount(0);
    const ac = new AbortController();
    abortRef.current = ac;
    const runId = `identify-${crypto.randomUUID().slice(0, 12)}`;

    try {
      await postSse(
        "/identify/run/stream",
        { topic, run_id: runId },
        (ev: SseEvent) => {
          if (ev.fallback) {
            setSourceChip("recorded", COPY.identify.fallback);
          }
          if (ev.verb && ev.body) {
            setLines((prev) => [
              ...prev,
              {
                id: `${ev.t}-${ev.verb}-${prev.length}`,
                t: ev.t ?? 0,
                verb: ev.verb ?? "",
                body: ev.body ?? "",
                status: ev.status,
                artifacts: ev.artifacts,
              },
            ]);
            if (!followRef.current) setNewCount((n) => n + 1);
            const urls = ev.artifacts?.urls;
            if (Array.isArray(urls)) {
              setSources((prev) => [...new Set([...prev, ...urls.map(String)])]);
            }
          }
          if (ev.status === "done" || ev.verb === "REPLAY") {
            setSession((prev) => ({
              ...prev,
              identify: { ...prev.identify, runId, topic },
            }));
            setStage("review");
            onCompleteRef.current?.();
          }
        },
        ac.signal,
      );
      if (!ac.signal.aborted) {
        setSession((prev) => ({
          ...prev,
          identify: { ...prev.identify, runId, topic },
        }));
        setStage("review");
        onCompleteRef.current?.();
      }
    } catch (e) {
      if ((e as { name?: string }).name === "AbortError") return;
      setError(COPY.identify.sseDrop);
      setSourceChip("recorded", COPY.identify.fallback);
      setStage("review");
    } finally {
      abortRef.current = null;
      setRunning(false);
    }
  }, []);

  const skip = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setRunning(false);
    setStage("review");
  }, []);

  useEffect(() => () => abortRef.current?.abort(), []);

  return {
    stage,
    setStage,
    lines,
    sources,
    running,
    error,
    discover,
    skip,
    follow,
    setFollow,
    newCount,
    clearNew: () => setNewCount(0),
  };
}
