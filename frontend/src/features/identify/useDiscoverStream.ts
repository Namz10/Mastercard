import { useCallback, useEffect, useRef, useState } from "react";
import { api, postSse, type SseEvent } from "@/lib/api-client";
import { COPY } from "@/lib/copy";
import { formatIstClock } from "@/lib/format";
import { subscribeRecordedIdentify, subscribeSkipIdentify } from "@/lib/identify-bus";
import { paceEvents, scheduleOffsets } from "@/lib/pace-events";
import { setSession, setSourceChip } from "@/lib/session-store";

export interface LogLine {
  id: string;
  t: number;
  verb: string;
  body: string;
  status?: string;
  clock?: string;
  artifacts?: Record<string, unknown>;
}

export type IdentifyStage = "rest" | "scanning" | "review";

function toLine(ev: SseEvent, index: number): LogLine {
  const verb = ev.verb ?? "";
  let body = ev.body ?? "";
  if (verb === "REPLAY" && !body.includes("recorded")) body = `${body} · recorded`;
  return {
    id: `${ev.t ?? 0}-${verb}-${index}`,
    t: ev.t ?? 0,
    verb,
    body,
    status: ev.status,
    clock: formatIstClock(),
    artifacts: ev.artifacts,
  };
}

function collectStarted(): SseEvent {
  return {
    t: 0,
    verb: "COLLECT",
    body: "started · FinCEN / RBI / OSINT",
    status: "ok",
  };
}

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
  const lineIndex = useRef(0);

  useEffect(() => {
    followRef.current = follow;
  }, [follow]);
  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  const appendEvent = useCallback((ev: SseEvent) => {
    const line = toLine(ev, lineIndex.current++);
    setLines((prev) => [...prev, line]);
    if (!followRef.current) setNewCount((n) => n + 1);
    const urls = ev.artifacts?.urls;
    if (Array.isArray(urls)) {
      setSources((prev) => [...new Set([...prev, ...urls.map(String)])]);
    }
  }, []);

  const finishReview = useCallback((runId: string, topic: string) => {
    setSession((prev) => ({
      ...prev,
      identify: { ...prev.identify, runId, topic },
    }));
    setStage("review");
    setRunning(false);
    abortRef.current = null;
    onCompleteRef.current?.();
  }, []);

  const playEvents = useCallback(
    async (events: SseEvent[], runId: string, topic: string, recorded: boolean, signal: AbortSignal) => {
      const toPlay = events.filter((e) => e.verb && e.body);
      if (recorded) {
        await paceEvents(toPlay, scheduleOffsets(toPlay), (ev) => appendEvent(ev), signal);
      } else {
        toPlay.forEach((ev) => appendEvent(ev));
      }
      if (!signal.aborted) finishReview(runId, topic);
    },
    [appendEvent, finishReview],
  );

  const discover = useCallback(
    async (topic = "") => {
      if (abortRef.current) return;
      setRunning(true);
      setStage("scanning");
      setLines([]);
      setSources([]);
      setError(null);
      setNewCount(0);
      lineIndex.current = 0;
      const ac = new AbortController();
      abortRef.current = ac;
      const runId = `identify-${crypto.randomUUID().slice(0, 12)}`;
      appendEvent(collectStarted());

      const buffered: SseEvent[] = [];
      let recorded = false;

      try {
        await postSse(
          "/identify/run/stream",
          { topic, run_id: runId },
          (ev: SseEvent) => {
            if (ev.fallback) {
              recorded = true;
              setSourceChip("recorded", ev.reason ?? COPY.identify.fallback);
            }
            if (ev.verb && ev.body) {
              if (ev.verb === "COLLECT" && ev.body.toLowerCase().includes("started") && lineIndex.current <= 1) {
                return;
              }
              if (recorded) buffered.push(ev);
              else appendEvent(ev);
            }
          },
          ac.signal,
        );
        if (ac.signal.aborted) return;
        if (recorded) {
          await playEvents(buffered, runId, topic, true, ac.signal);
        } else {
          setSourceChip("live");
          finishReview(runId, topic);
        }
      } catch (e) {
        if ((e as { name?: string }).name === "AbortError") return;
        setError(COPY.identify.sseDrop);
        setSourceChip("recorded", COPY.identify.fallback);
        try {
          const pack = await api.get<{ events: SseEvent[]; run_id: string }>("/demo/recorded/identify");
          await playEvents(pack.events ?? [], pack.run_id ?? runId, topic, true, ac.signal);
        } catch {
          finishReview(runId, topic);
        }
      }
    },
    [appendEvent, finishReview, playEvents],
  );

  const playRecorded = useCallback(async () => {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setRunning(true);
    setStage("scanning");
    setLines([]);
    setSources([]);
    setError(null);
    setNewCount(0);
    lineIndex.current = 0;
    setSourceChip("recorded", COPY.identify.fallback);
    appendEvent(collectStarted());
    try {
      const pack = await api.get<{ events: SseEvent[]; run_id: string }>("/demo/recorded/identify");
      const rest = (pack.events ?? []).filter(
        (e) => !(e.verb === "COLLECT" && (e.body ?? "").toLowerCase().includes("started")),
      );
      await playEvents(rest, pack.run_id ?? "recorded-identify", "", true, ac.signal);
    } catch {
      setError(COPY.identify.sseDrop);
      finishReview("recorded-identify", "");
    }
  }, [appendEvent, finishReview, playEvents]);

  const skip = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setRunning(false);
    setStage("review");
    onCompleteRef.current?.();
  }, []);

  useEffect(() => subscribeRecordedIdentify(() => void playRecorded()), [playRecorded]);
  useEffect(() => subscribeSkipIdentify(() => skip()), [skip]);
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
    playRecorded,
    follow,
    setFollow,
    newCount,
    clearNew: () => setNewCount(0),
  };
}
