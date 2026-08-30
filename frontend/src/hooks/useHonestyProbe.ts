import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import { setSourceChip, useSessionSnapshot, type SourceMode } from "@/lib/session-store";

export interface HonestyConfig {
  identify_live_search: boolean;
  tavily_configured: boolean;
  llm: { configured?: boolean };
}

interface Health {
  status: string;
}

export interface HonestyProbe {
  tavily: boolean;
  llm: boolean;
  liveSearch: boolean;
  health: boolean;
  loaded: boolean;
}

export function liveAllowed(config: HonestyConfig | null, health: Health | null): boolean {
  return Boolean(config?.identify_live_search && config?.llm?.configured && health?.status === "ok");
}

/** LIVE only if search + LLM + health. Never invent live. Frozen/recorded stay. */
export function useHonestyProbe(): HonestyProbe {
  const session = useSessionSnapshot();
  const [probe, setProbe] = useState<HonestyProbe>({
    tavily: false,
    llm: false,
    liveSearch: false,
    health: false,
    loaded: false,
  });

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const [config, health] = await Promise.all([
        api.get<HonestyConfig>("/identify/config").catch(() => null),
        api.get<Health>("/health").catch(() => null),
      ]);
      if (cancelled) return;
      const next: HonestyProbe = {
        tavily: Boolean(config?.tavily_configured),
        llm: Boolean(config?.llm?.configured),
        liveSearch: Boolean(config?.identify_live_search),
        health: health?.status === "ok",
        loaded: true,
      };
      setProbe(next);
      const ok = liveAllowed(config, health);
      const current: SourceMode = session.ui.sourceChip;
      if (current === "frozen" || current === "rules") return;
      if (ok && (current === "recorded" || current === "live") && !session.ui.recordedReason) {
        setSourceChip("live");
      } else if (!ok && current === "live") {
        setSourceChip("recorded");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [session.ui.sourceChip, session.ui.recordedReason]);

  return probe;
}
