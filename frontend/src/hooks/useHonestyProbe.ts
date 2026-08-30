import { useEffect } from "react";
import { api } from "@/lib/api-client";
import { setSourceChip, useSessionSnapshot, type SourceMode } from "@/lib/session-store";

interface IdentifyConfig {
  identify_live_search: boolean;
  tavily_configured: boolean;
  llm: { configured?: boolean };
}

interface Health {
  status: string;
}

export function liveAllowed(config: IdentifyConfig | null, health: Health | null): boolean {
  return Boolean(config?.identify_live_search && config?.llm?.configured && health?.status === "ok");
}

/** LIVE only if search + LLM + health. Never invent live. Frozen/recorded stay. */
export function useHonestyProbe() {
  const session = useSessionSnapshot();

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const [config, health] = await Promise.all([
        api.get<IdentifyConfig>("/identify/config").catch(() => null),
        api.get<Health>("/health").catch(() => null),
      ]);
      if (cancelled) return;
      const ok = liveAllowed(config, health);
      const current: SourceMode = session.ui.sourceChip;
      if (current === "frozen" || current === "rules") return;
      if (ok && !session.ui.recordedReason) setSourceChip("live");
      else if (!ok && current === "live") setSourceChip("recorded");
    })();
    return () => {
      cancelled = true;
    };
  }, [session.ui.sourceChip]);
}
