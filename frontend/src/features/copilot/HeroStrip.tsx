import { useNavigate } from "react-router-dom";
import clsx from "clsx";
import { formatNum, formatPct } from "@/lib/format";
import type { CommandCenterKpis, CommandCenterSystem } from "./command-types";

function fmtMs(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return "—";
  return `${formatNum(v, v >= 10 ? 0 : 1)} ms`;
}

function fmtDelta(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return "—";
  const sign = v > 0 ? "+" : "";
  return `${sign}${formatPct(v, 2)}`;
}

const KPI_DEFS: {
  key: keyof CommandCenterKpis | "atlas";
  label: string;
  hint: string;
  to: string;
  value: (k: CommandCenterKpis) => string;
}[] = [
  {
    key: "atlas",
    label: "Atlas coverage",
    hint: "T01–T24",
    to: "/",
    value: (k) => k.atlas_techniques || (k.atlas_count != null ? `${k.atlas_count} / 24` : "—"),
  },
  {
    key: "live_rules",
    label: "v0 rules",
    hint: "live_rule cells",
    to: "/",
    value: (k) => (k.live_rules != null ? String(k.live_rules) : "—"),
  },
  {
    key: "hitl_pending",
    label: "Awaiting approve",
    hint: "HITL pending",
    to: "/identify",
    value: (k) => (k.hitl_pending != null ? String(k.hitl_pending) : "—"),
  },
  {
    key: "loop_m_ap_delta",
    label: "Loop M",
    hint: "AP delta",
    to: "/arms-race",
    value: (k) => fmtDelta(k.loop_m_ap_delta),
  },
  {
    key: "genuine_fpr",
    label: "Genuine holdout",
    hint: "FPR",
    to: "/decisioning",
    value: (k) => formatPct(k.genuine_fpr, 2),
  },
  {
    key: "authgate_p50_ms",
    label: "AuthGate",
    hint: "p50 latency",
    to: "/decisioning",
    value: (k) => fmtMs(k.authgate_p50_ms),
  },
];

function systemPills(system: CommandCenterSystem): { label: string; ok: boolean }[] {
  const llmOk =
    system.llm &&
    (system.llm.configured === true ||
      system.llm.ready === true ||
      system.llm.status === "ok" ||
      system.llm.provider != null);
  return [
    { label: "postgres", ok: Boolean(system.postgres) },
    { label: "pgvector", ok: Boolean(system.pgvector) },
    { label: "tavily", ok: Boolean(system.tavily_configured) },
    { label: "llm", ok: Boolean(llmOk) },
    { label: "live_search", ok: Boolean(system.identify_live_search) },
  ];
}

export function HeroStrip({
  kpis,
  system,
  generatedAt,
}: {
  kpis: CommandCenterKpis;
  system: CommandCenterSystem;
  generatedAt: string | null;
}) {
  const navigate = useNavigate();
  const pills = systemPills(system);
  const updated =
    generatedAt != null
      ? (() => {
          try {
            return new Date(generatedAt).toLocaleTimeString();
          } catch {
            return generatedAt;
          }
        })()
      : "—";

  return (
    <section className="relative overflow-hidden rounded-xl border border-border bg-[#e8eae6] min-h-[120px] px-5 py-4 mb-8">
      <div className="flex flex-wrap items-end justify-between gap-3 mb-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-ink">AegisLoop Command Center</h1>
          <p className="text-xs text-ink-muted mt-0.5">
            Identify → Generate → Defend → Evolve · synthetic lab only · LLM off authorization path
          </p>
          <p className="font-mono text-[10px] text-ink-faint mt-1">last updated {updated}</p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <span
            className={clsx(
              "font-mono text-[10px] uppercase tracking-wide px-2 py-0.5 rounded-sm border",
              system.status === "ok"
                ? "border-[#166534]/40 text-[#166534] bg-green-50"
                : "border-amber-500/40 text-amber-800 bg-amber-50",
            )}
          >
            system {system.status || "—"}
          </span>
          {pills.map((p) => (
            <span
              key={p.label}
              className={clsx(
                "font-mono text-[10px] uppercase tracking-wide px-2 py-0.5 rounded-sm border",
                p.ok
                  ? "border-border-strong text-ink-muted bg-white"
                  : "border-border text-ink-faint bg-surface-sunken",
              )}
            >
              {p.label}
            </span>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
        {KPI_DEFS.map((kpi) => (
          <button
            key={kpi.label}
            type="button"
            onClick={() => navigate(kpi.to)}
            className="text-left rounded-lg border border-border bg-white px-3 py-2.5 hover:bg-surface-sunken transition-colors"
          >
            <div className="font-mono text-lg font-medium tabular-nums leading-tight text-ink">
              {kpi.value(kpis)}
            </div>
            <div className="font-mono text-[10px] uppercase tracking-wide text-ink-faint mt-1">
              {kpi.label}
            </div>
            <div className="font-mono text-[10px] text-ink-faint/80 mt-0.5">{kpi.hint}</div>
          </button>
        ))}
      </div>
    </section>
  );
}
