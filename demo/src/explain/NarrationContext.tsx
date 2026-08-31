import { createContext, useContext, useState, type ReactNode } from "react";
import type { SseEvent } from "@/lib/api-client";
import { fallbackNarration } from "@/content/live-narration";
import { setNarrationListener } from "@/lib/api-client";
import { useEffect } from "react";

export interface NarrationState {
  now: string;
  why: string;
  happening: string;
  next?: string;
  visual?: string;
  verb?: string;
  elapsedMs?: number;
  artifacts?: Record<string, unknown>;
}

const NarrationContext = createContext<{
  narration: NarrationState | null;
  setNarration: (n: NarrationState | null) => void;
  captionsHidden: boolean;
  setCaptionsHidden: (v: boolean) => void;
} | null>(null);

export function NarrationProvider({ children }: { children: ReactNode }) {
  const [narration, setNarration] = useState<NarrationState | null>(null);
  const [captionsHidden, setCaptionsHidden] = useState(false);
  const [start, setStart] = useState<number | null>(null);

  useEffect(() => {
    setNarrationListener((ev) => {
      const fb = fallbackNarration(ev.verb ?? "", ev.body ?? "");
      setStart((s) => s ?? Date.now());
      setNarration({
        now: ev.now ?? fb.now,
        why: ev.why ?? fb.why,
        happening: ev.happening ?? fb.happening,
        next: ev.next,
        visual: ev.visual,
        verb: ev.verb,
        artifacts: ev.artifacts,
        elapsedMs: start ? Date.now() - (start ?? Date.now()) : 0,
      });
    });
    return () => setNarrationListener(null);
  }, [start]);

  return (
    <NarrationContext.Provider
      value={{ narration, setNarration, captionsHidden, setCaptionsHidden }}
    >
      {children}
    </NarrationContext.Provider>
  );
}

export function useNarration() {
  const ctx = useContext(NarrationContext);
  if (!ctx) throw new Error("useNarration requires NarrationProvider");
  return ctx;
}

export function applyNarrationFromEvent(ev: SseEvent, setNarration: (n: NarrationState) => void) {
  const fb = fallbackNarration(ev.verb ?? "", ev.body ?? "");
  setNarration({
    now: ev.now ?? fb.now,
    why: ev.why ?? fb.why,
    happening: ev.happening ?? fb.happening,
    next: ev.next,
    visual: ev.visual,
    verb: ev.verb,
  });
}
