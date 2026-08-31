import { createContext, createElement, useCallback, useContext, useMemo, useSyncExternalStore, type ReactNode } from "react";
import type { ScoreResponse } from "@/lib/api-types";
import { STORAGE_KEYS } from "@/lib/storage-keys";

export type SourceMode = "live" | "recorded" | "frozen" | "rules";

export interface ApprovedAttack {
  id: string;
  techniqueId: string;
  name: string;
}

export interface AegisSession {
  identify: {
    topic: string;
    runId: string | null;
    source: SourceMode;
    proposedIds: string[];
    approved: ApprovedAttack[];
  };
  generate: {
    runId: string | null;
    seed: number | null;
    scale: "demo" | "full";
    fidelityPass: boolean | null;
    fidelityReasons: string[] | null;
    eventCount: number | null;
    familyCounts: Record<string, number> | null;
    muleFanIn: number | null;
  };
  defend: {
    modelRunId: string | null;
    score: ScoreResponse | null;
    scoreBeforeRetrain: ScoreResponse | null;
    missTechniqueId: string | null;
    loopResult: Record<string, unknown> | null;
    stage2ModelId: string | null;
    tuneResult: Record<string, unknown> | null;
    tunedScore: ScoreResponse | null;
  };
  ui: {
    highlightTechniqueId: string | null;
    sourceChip: SourceMode;
    recordedReason: string | null;
  };
}

const DEFAULT_SESSION: AegisSession = {
  identify: { topic: "", runId: null, source: "live", proposedIds: [], approved: [] },
  generate: {
    runId: null,
    seed: null,
    scale: "full",
    fidelityPass: null,
    fidelityReasons: null,
    eventCount: null,
    familyCounts: null,
    muleFanIn: null,
  },
  defend: {
    modelRunId: null,
    score: null,
    scoreBeforeRetrain: null,
    missTechniqueId: null,
    loopResult: null,
    stage2ModelId: null,
    tuneResult: null,
    tunedScore: null,
  },
  ui: { highlightTechniqueId: null, sourceChip: "recorded", recordedReason: "Booth prototype" },
};

let sessionCache: AegisSession = loadSession();
const listeners = new Set<() => void>();

function loadSession(): AegisSession {
  if (typeof window === "undefined") return structuredClone(DEFAULT_SESSION);
  try {
    localStorage.removeItem(STORAGE_KEYS.session);
    const raw = sessionStorage.getItem(STORAGE_KEYS.session);
    if (!raw) return structuredClone(DEFAULT_SESSION);
    const parsed = JSON.parse(raw) as Partial<AegisSession>;
    return {
      identify: { ...DEFAULT_SESSION.identify, ...parsed.identify },
      generate: { ...DEFAULT_SESSION.generate, ...parsed.generate },
      defend: { ...DEFAULT_SESSION.defend, ...parsed.defend },
      ui: { ...DEFAULT_SESSION.ui, ...parsed.ui },
    };
  } catch {
    return structuredClone(DEFAULT_SESSION);
  }
}

function persist(next: AegisSession) {
  sessionCache = next;
  if (typeof window !== "undefined") {
    sessionStorage.setItem(STORAGE_KEYS.session, JSON.stringify(next));
    localStorage.removeItem(STORAGE_KEYS.session);
  }
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSnapshot() {
  return sessionCache;
}

export function getSession(): AegisSession {
  return sessionCache;
}

export function setSession(patch: Partial<AegisSession> | ((prev: AegisSession) => AegisSession)) {
  const next = typeof patch === "function" ? patch(sessionCache) : { ...sessionCache, ...patch };
  persist(next);
}

export function updateSession<K extends keyof AegisSession>(key: K, value: AegisSession[K]) {
  persist({ ...sessionCache, [key]: value });
}

export function setGenerateRun(
  runId: string,
  seed: number,
  scale: "demo" | "full",
  fidelityPass: boolean,
  eventCount: number,
  familyCounts: Record<string, number> | null = null,
  muleFanIn: number | null = null,
  fidelityReasons: string[] | null = null,
) {
  persist({
    ...sessionCache,
    generate: { runId, seed, scale, fidelityPass, fidelityReasons, eventCount, familyCounts, muleFanIn },
    defend: {
      modelRunId: null,
      score: null,
      scoreBeforeRetrain: null,
      missTechniqueId: null,
      loopResult: null,
      stage2ModelId: null,
      tuneResult: null,
      tunedScore: null,
    },
  });
}

export function setTuneResult(
  tunedScore: ScoreResponse,
  stage2ModelId: string,
  tuneResult: Record<string, unknown>,
) {
  persist({
    ...sessionCache,
    defend: {
      ...sessionCache.defend,
      tunedScore,
      stage2ModelId,
      tuneResult,
    },
  });
}

export function setDefendScore(score: ScoreResponse, modelRunId: string) {
  persist({
    ...sessionCache,
    defend: {
      ...sessionCache.defend,
      score,
      modelRunId,
    },
  });
}

export function setRetrainResult(
  scoreAfter: ScoreResponse,
  modelRunId: string,
  missTechniqueId: string,
  loopResult: Record<string, unknown>,
  scoreBefore?: ScoreResponse | null,
) {
  persist({
    ...sessionCache,
    defend: {
      ...sessionCache.defend,
      scoreBeforeRetrain: scoreBefore ?? sessionCache.defend.score,
      score: scoreAfter,
      modelRunId,
      missTechniqueId,
      loopResult,
    },
    ui: { ...sessionCache.ui, highlightTechniqueId: missTechniqueId },
  });
}

export function acceptCatalogSeed() {
  if (sessionCache.identify.approved.length > 0) return;
  persist({
    ...sessionCache,
    identify: {
      ...sessionCache.identify,
      approved: [{ id: "catalog-seed", techniqueId: "T13", name: "Catalog seed" }],
      source: "recorded",
    },
    ui: { ...sessionCache.ui, sourceChip: "recorded", recordedReason: "Catalog seed" },
  });
}

export function approveAttack(attack: ApprovedAttack) {
  const approved = sessionCache.identify.approved.some(
    (a) => a.id === attack.id || a.techniqueId === attack.techniqueId,
  )
    ? sessionCache.identify.approved
    : [...sessionCache.identify.approved, attack];
  persist({
    ...sessionCache,
    identify: { ...sessionCache.identify, approved },
  });
}

export function setSourceChip(mode: SourceMode, reason?: string | null) {
  const nextReason = reason !== undefined ? reason : sessionCache.ui.recordedReason;
  if (
    sessionCache.ui.sourceChip === mode &&
    sessionCache.ui.recordedReason === nextReason &&
    sessionCache.identify.source === mode
  ) {
    return;
  }
  persist({
    ...sessionCache,
    identify: { ...sessionCache.identify, source: mode },
    ui: { ...sessionCache.ui, sourceChip: mode, recordedReason: nextReason ?? null },
  });
}

type Phase = "identify" | "generate" | "defend";

export function phaseStatus(phase: Phase): "idle" | "in_progress" | "ready" | "done" {
  const s = sessionCache;
  if (phase === "identify") {
    if (s.identify.approved.length > 0 || s.generate.runId) return "done";
    if (s.identify.runId) return "ready";
    return "idle";
  }
  if (phase === "generate") {
    if (s.generate.fidelityPass != null) return "done";
    if (s.generate.runId) return "in_progress";
    return s.identify.approved.length > 0 ? "ready" : "idle";
  }
  if (s.defend.score) return "done";
  if (s.generate.fidelityPass != null) return "ready";
  return "idle";
}

const SessionContext = createContext<{
  session: AegisSession;
  setSession: typeof setSession;
  updateSession: typeof updateSession;
} | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const session = useSyncExternalStore(subscribe, getSnapshot, () => DEFAULT_SESSION);

  const stableSet = useCallback((patch: Parameters<typeof setSession>[0]) => setSession(patch), []);
  const stableUpdate = useCallback(
    <K extends keyof AegisSession>(key: K, value: AegisSession[K]) => updateSession(key, value),
    [],
  );

  const value = useMemo(
    () => ({ session, setSession: stableSet, updateSession: stableUpdate }),
    [session, stableSet, stableUpdate],
  );

  return createElement(SessionContext.Provider, { value }, children);
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used within SessionProvider");
  return ctx;
}

export function useSessionSnapshot() {
  return useSyncExternalStore(subscribe, getSnapshot, () => DEFAULT_SESSION);
}

export function resetSessionForTests() {
  beginBoothSession();
}

/** Fresh booth — no prior generate/defend/identify progress on glass. */
export function beginBoothSession() {
  persist(structuredClone(DEFAULT_SESSION));
}

export function clearDefendIfStale() {
  const s = sessionCache;
  if (!s.defend.score) return;
  if (!s.generate.runId) {
    persist({
      ...s,
      defend: { ...DEFAULT_SESSION.defend },
    });
    return;
  }
  if (s.defend.score.run_id !== s.generate.runId) {
    persist({
      ...s,
      defend: { ...DEFAULT_SESSION.defend },
    });
  }
}

export function isDefendScoreCurrent(session: AegisSession = sessionCache): boolean {
  if (!session.defend.score || !session.generate.runId) return false;
  return session.defend.score.run_id === session.generate.runId;
}

export function canScoreGenerate(session: AegisSession = sessionCache): boolean {
  return Boolean(session.generate.runId);
}
