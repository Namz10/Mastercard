import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import { getSession, setSourceChip } from "@/lib/session-store";

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

let probeInflight: Promise<HonestyProbe> | null = null;

async function fetchHonestyProbe(): Promise<HonestyProbe> {
  const [config, health] = await Promise.all([
    api.get<HonestyConfig>("/identify/config").catch(() => null),
    api.get<Health>("/health").catch(() => null),
  ]);
  const next: HonestyProbe = {
    tavily: Boolean(config?.tavily_configured),
    llm: Boolean(config?.llm?.configured),
    liveSearch: Boolean(config?.identify_live_search),
    health: health?.status === "ok",
    loaded: true,
  };
  applySourceChipFromProbe(config, health);
  return next;
}

function applySourceChipFromProbe(config: HonestyConfig | null, health: Health | null) {
  const ok = liveAllowed(config, health);
  const { sourceChip: current, recordedReason } = getSession().ui;
  if (current === "frozen" || current === "rules") return;
  if (ok && (current === "recorded" || current === "live") && !recordedReason) {
    setSourceChip("live");
  } else if (!ok && current === "live") {
    setSourceChip("recorded");
  }
}

export function ensureHonestyProbe(): Promise<HonestyProbe> {
  if (!probeInflight) {
    probeInflight = fetchHonestyProbe().finally(() => {
      probeInflight = null;
    });
  }
  return probeInflight;
}

/** One-shot honesty check on workspace load — never poll, never re-run on chip changes. */
export function useHonestyProbe(): HonestyProbe {
  const [probe, setProbe] = useState<HonestyProbe>({
    tavily: false,
    llm: false,
    liveSearch: false,
    health: false,
    loaded: false,
  });

  useEffect(() => {
    let cancelled = false;
    void ensureHonestyProbe().then((next) => {
      if (!cancelled) setProbe(next);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return probe;
}

export function resetHonestyProbeForTests() {
  probeInflight = null;
}
