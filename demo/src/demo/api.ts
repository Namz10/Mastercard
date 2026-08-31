import { replayTimeline, type TimelineEvent } from "./replayer";

const PACK_BASE = "/packs";

async function loadPack<T>(path: string): Promise<T> {
  const res = await fetch(`${PACK_BASE}/${path}`);
  if (!res.ok) throw new Error(`Pack not found: ${path}`);
  return res.json() as Promise<T>;
}

const STREAM_MAP: Record<string, string> = {
  "/identify/run/stream": "timelines/identify.json",
  "/generate/population/stream": "timelines/generate.json",
  "/defend/fit/stream": "timelines/fit.json",
  "/defend/loop-m/stream": "timelines/loop-m.json",
  "/defend/tune/stream": "timelines/tune.json",
};

export const demoApi = {
  async get<T>(path: string): Promise<T> {
    switch (path) {
      case "/health":
        return { status: "ok", mode: "recorded" } as T;
      case "/identify/config":
        return {
          identify_live_search: false,
          tavily_configured: false,
          live_osint: false,
          recorded_fallback: true,
          llm: { configured: false },
        } as T;
      case "/demo/recorded/score":
        return loadPack("score-champion.json");
      case "/demo/recorded/loop":
        return loadPack("loop-m-champion.json");
      case "/demo/recorded/identify":
        return loadPack("timelines/identify.json");
      case "/catalog/threat-map":
        return loadPack("threat-map.json");
      case "/defend/coverage-map":
        return loadPack("coverage-map.json");
      case "/identify/hitl":
        return loadPack("hitl-queue.json");
      case "/generate/eligible":
        return { count: 3, items: [] } as T;
      default:
        if (path.startsWith("/demo/recorded/")) {
          if (path.includes("score")) return loadPack("score-champion.json");
          if (path.includes("loop")) return loadPack("loop-m-champion.json");
        }
        throw new Error(`Demo API: unknown GET ${path}`);
    }
  },

  async post<T>(path: string, body?: unknown): Promise<T> {
    if (path === "/defend/score") {
      const req = body as { model_run_id?: string } | undefined;
      if (req?.model_run_id?.includes("tuned")) {
        return loadPack("score-tuned.json");
      }
      return loadPack("score-champion.json");
    }
    if (path === "/identify/approve") {
      return { ok: true } as T;
    }
    throw new Error(`Demo API: unknown POST ${path}`);
  },

  async postSse(
    path: string,
    _body: unknown,
    onEvent: (event: import("@/lib/api-client").SseEvent) => void,
    signal?: AbortSignal,
    onNarration?: (ev: TimelineEvent) => void,
  ): Promise<void> {
    const packPath = STREAM_MAP[path];
    if (!packPath) throw new Error(`Demo API: unknown stream ${path}`);
    const doc = await loadPack<{ events: TimelineEvent[] }>(packPath);
    const result = await replayTimeline(doc.events, onEvent, onNarration, signal);
    if (!result) throw new Error("Stream ended without result");
  },
};
