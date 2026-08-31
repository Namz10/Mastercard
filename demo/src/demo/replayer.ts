import type { SseEvent } from "@/lib/api-client";
import { captionPauseMs, parseSpeedMode, timingScale } from "./speed";

export interface TimelineEvent extends SseEvent {
  now?: string;
  why?: string;
  happening?: string;
  next?: string;
  visual?: string;
}

export type NarrationListener = (ev: TimelineEvent) => void;

export async function replayTimeline(
  events: TimelineEvent[],
  onEvent: (ev: SseEvent) => void,
  onNarration?: NarrationListener,
  signal?: AbortSignal,
): Promise<Record<string, unknown> | null> {
  const mode = parseSpeedMode();
  const scale = timingScale(mode);
  const pauseMs = captionPauseMs(mode);
  let result: Record<string, unknown> | null = null;
  let lastT = 0;

  for (const ev of events) {
    if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
    const delay = scale === 0 ? 0 : Math.max(0, (ev.t ?? 0) - lastT) * scale;
    lastT = ev.t ?? lastT;
    if (delay > 0) {
      await sleep(delay, signal);
    }
    if (onNarration && (ev.now || ev.why || ev.happening)) {
      onNarration(ev);
      if (pauseMs > 0 && ev.now) {
        await sleep(pauseMs, signal);
      }
    }
    onEvent(ev);
    if (ev.status === "done" && ev.result) {
      result = ev.result as Record<string, unknown>;
    }
  }
  return result;
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  if (ms <= 0) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const t = setTimeout(() => {
      signal?.removeEventListener("abort", onAbort);
      resolve();
    }, ms);
    const onAbort = () => {
      clearTimeout(t);
      reject(new DOMException("Aborted", "AbortError"));
    };
    signal?.addEventListener("abort", onAbort);
  });
}
