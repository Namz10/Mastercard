import { demoApi } from "@/demo/api";
import type { TimelineEvent } from "@/demo/replayer";

const LIVE_BASE = import.meta.env.VITE_API_BASE_URL as string | undefined;
const USE_LIVE = Boolean(LIVE_BASE);

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export interface SseEvent {
  t?: number;
  verb?: string;
  body?: string;
  status?: string;
  artifacts?: Record<string, unknown>;
  fallback?: string;
  reason?: string;
  result?: Record<string, unknown>;
  now?: string;
  why?: string;
  happening?: string;
  next?: string;
  visual?: string;
}

type NarrationCb = (ev: TimelineEvent) => void;

let narrationListener: NarrationCb | null = null;

export function setNarrationListener(cb: NarrationCb | null) {
  narrationListener = cb;
}

async function liveRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${LIVE_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(res.status, body || res.statusText);
  }
  return res.json() as Promise<T>;
}

export async function postSse(
  path: string,
  body: unknown,
  onEvent: (event: SseEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  if (!USE_LIVE) {
    await demoApi.postSse(path, body, onEvent, signal, (ev) => {
      narrationListener?.(ev);
    });
    return;
  }

  const res = await fetch(`${LIVE_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new ApiError(res.status, text || res.statusText);
  }
  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data:")) continue;
      const json = line.slice(5).trim();
      if (!json) continue;
      try {
        onEvent(JSON.parse(json) as SseEvent);
      } catch {
        /* ignore */
      }
    }
  }
}

export const api = {
  get: <T>(path: string) =>
    USE_LIVE ? liveRequest<T>(path) : demoApi.get<T>(path),
  post: <T>(path: string, body?: unknown) =>
    USE_LIVE
      ? liveRequest<T>(path, {
          method: "POST",
          body: body ? JSON.stringify(body) : undefined,
        })
      : demoApi.post<T>(path, body),
};

export function isRecordedDemo(): boolean {
  return !USE_LIVE;
}
