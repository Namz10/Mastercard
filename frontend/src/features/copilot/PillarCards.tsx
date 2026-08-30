import { Link } from "react-router-dom";
import { formatInt, formatPct } from "@/lib/format";
import type { CommandCenterSnapshot } from "./command-types";

const PILLARS: {
  id: string;
  label: string;
  to: string;
  blurb: (s: CommandCenterSnapshot) => string;
  meta: (s: CommandCenterSnapshot) => string;
}[] = [
  {
    id: "identify",
    label: "Identify",
    to: "/identify",
    blurb: (s) => {
      const topic = s.identify.last_run?.topic || s.identify.last_topic;
      const run = s.identify.last_run?.run_id;
      if (topic && run) return `${topic} · ${run}`;
      if (topic) return `Last topic · ${topic}`;
      return "Topic research → HITL queue";
    },
    meta: (s) => {
      const proposed = s.identify.last_run?.proposed_count;
      const extra = proposed == null ? "" : ` · proposed ${formatInt(Number(proposed))}`;
      return `pending ${formatInt(s.identify.hitl_pending)} · approved ${formatInt(s.identify.hitl_approved)}${extra}`;
    },
  },
  {
    id: "generate",
    label: "Generate",
    to: "/simulation",
    blurb: (s) => {
      const run = s.generate.last_run;
      return run?.run_id
        ? `${run.mode ?? "run"} · ${run.run_id}`
        : "ShadowRail population / canary";
    },
    meta: (s) => {
      const run = s.generate.last_run;
      const fid = run?.fidelity?.pass;
      const rows = run?.row_count;
      return `rows ${formatInt(rows ?? null)} · fidelity ${fid == null ? "—" : fid ? "pass" : "fail"}`;
    },
  },
  {
    id: "defend",
    label: "Defend",
    to: "/decisioning",
    blurb: (s) =>
      s.defend.champion_run_id
        ? `Champion · ${s.defend.champion_run_id}`
        : "AuthGate + Brake scoring",
    meta: (s) => {
      const m = s.defend.metrics;
      return `AP ${formatPct(m.binary_ap)} · FPR ${formatPct(m.genuine_fp, 3)} · drafts ${formatInt(s.defend.drafts_pending)}`;
    },
  },
  {
    id: "evolve",
    label: "Evolve",
    to: "/arms-race",
    blurb: () => "Loop M · analyst approval required",
    meta: (s) => {
      const delta = s.evolve.loop_m_last?.ap_delta;
      const q = s.evolve.retrain_queue?.length ?? 0;
      const deltaStr =
        delta == null || Number.isNaN(delta)
          ? "—"
          : `${delta >= 0 ? "+" : ""}${formatPct(delta, 2)}`;
      return `ΔAP ${deltaStr} · queue ${q} · catalog_solved false`;
    },
  },
];

export function PillarCards({ snapshot }: { snapshot: CommandCenterSnapshot }) {
  return (
    <section className="flex flex-col gap-3 h-full">
      <div className="font-mono uppercase text-ink-faint text-xs tracking-wide px-0.5">
        Pillars
      </div>
      {PILLARS.map((p) => (
        <Link
          key={p.id}
          to={p.to}
          className="block bg-white border border-border rounded-xl px-4 py-3 hover:bg-surface-sunken transition-colors"
        >
          <div className="flex items-baseline justify-between gap-2 mb-1">
            <span className="font-mono text-xs font-semibold uppercase tracking-wide text-[#166534]">
              {p.label}
            </span>
            <span className="font-mono text-[10px] text-ink-faint">→</span>
          </div>
          <div className="text-sm text-ink mb-1 truncate">{p.blurb(snapshot)}</div>
          <div className="font-mono text-[11px] text-ink-muted">{p.meta(snapshot)}</div>
        </Link>
      ))}
    </section>
  );
}
