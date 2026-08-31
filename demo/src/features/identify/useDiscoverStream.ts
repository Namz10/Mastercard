import { useCallback, useEffect, useRef, useState } from "react";
import { api, postSse, type SseEvent } from "@/lib/api-client";
import { COPY } from "@/lib/copy";
import { formatIstClock } from "@/lib/format";
import { mapDiscoverCatalogLine, mergeCatalogLine } from "@/lib/discover-catalog-map";
import { subscribeRecordedIdentify, subscribeSkipIdentify } from "@/lib/identify-bus";
import { paceEvents, scheduleOffsets } from "@/lib/pace-events";
import { setSession, setSourceChip } from "@/lib/session-store";

import type { OpsTapeLine } from "@/lib/ops-tape-types";

export type LogLine = OpsTapeLine;

export type IdentifyStage = "rest" | "scanning" | "review";

function extractUrlsFromText(text: string): string[] {
  const matches = text.match(/https?:\/\/[^\s"'<>]+/g) ?? [];
  return matches.map((u) => u.replace(/[),.;]+$/, ""));
}

function normalizeUrlEntry(u: unknown): string | null {
  if (typeof u === "string") return u;
  if (u && typeof u === "object" && "url" in u) return String((u as { url: string }).url);
  return null;
}

function collectUrls(ev: SseEvent): string[] {
  const found: string[] = [];
  const artifacts = ev.artifacts;
  if (artifacts?.urls && Array.isArray(artifacts.urls)) {
    for (const u of artifacts.urls) {
      const url = normalizeUrlEntry(u);
      if (url) found.push(url);
    }
  }
  const result = ev.result as { candidate_urls?: unknown[] } | undefined;
  if (result?.candidate_urls && Array.isArray(result.candidate_urls)) {
    for (const u of result.candidate_urls) {
      const url = normalizeUrlEntry(u);
      if (url) found.push(url);
    }
  }
  if (ev.body) found.push(...extractUrlsFromText(ev.body));
  return found;
}

function toLine(ev: SseEvent, index: number): LogLine | null {
  const rawVerb = ev.verb ?? "";
  const mapped = mapDiscoverCatalogLine(rawVerb, ev.body ?? "");
  if (mapped.skip) return null;
  return {
    id: `${ev.t ?? 0}-${mapped.verb}-${index}`,
    t: ev.t ?? 0,
    verb: mapped.verb,
    body: mapped.body,
    status: ev.status,
    clock: formatIstClock(),
    artifacts: ev.artifacts,
  };
}

function collectStarted(): SseEvent {
  return {
    t: 0,
    verb: "COLLECT",
    body: "Open allowlisted OSINT collectors",
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
    if (!line) return;
    setLines((prev) => mergeCatalogLine(prev, line));
    if (!followRef.current) setNewCount((n) => n + 1);
    const urls = collectUrls(ev);
    if (urls.length > 0) {
      setSources((prev) => [...new Set([...prev, ...urls])]);
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
      setSession((prev) => ({
        ...prev,
        identify: { ...prev.identify, runId: null, topic },
      }));
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
        setRunning(false);
        abortRef.current = null;
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
