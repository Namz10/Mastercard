import { formatNum, formatPct } from "@/lib/format";
import type { CommandCenterSnapshot } from "./command-types";

function EthicsChips({ ethics }: { ethics: CommandCenterSnapshot["ethics"] }) {
  const chips: { label: string; ok: boolean }[] = [
    { label: "synthetic_only", ok: ethics.synthetic_only },
    { label: "catalog_solved=false", ok: !ethics.catalog_solved },
    { label: "cat4_public_api=false", ok: !ethics.cat4_public_api },
    { label: "llm_not_detector", ok: ethics.llm_not_detector },
  ];
  return (
    <div className="flex flex-wrap gap-1.5 mt-3">
      {chips.map((c) => (
        <span
          key={c.label}
          className="font-mono text-[10px] uppercase tracking-wide px-2 py-0.5 rounded-sm border border-border text-ink-muted bg-surface-sunken"
        >
          {c.label}
        </span>
      ))}
    </div>
  );
}

export function ReportCards({ snapshot }: { snapshot: CommandCenterSnapshot }) {
  const m = snapshot.defend.metrics;
  const fid = snapshot.generate.last_run?.fidelity ?? snapshot.generate.fidelity ?? {};
  const fidelityPass =
    typeof fid === "object" && fid != null && "pass" in fid
      ? (fid as { pass?: boolean | null }).pass
      : null;
  const psiAmount =
    typeof fid === "object" && fid != null && "psi_amount" in fid
      ? (fid as { psi_amount?: number | null }).psi_amount
      : null;
  const psiHour =
    typeof fid === "object" && fid != null && "psi_hour" in fid
      ? (fid as { psi_hour?: number | null }).psi_hour
      : null;
  const fraudRate =
    typeof fid === "object" && fid != null && "fraud_rate" in fid
      ? (fid as { fraud_rate?: number | null }).fraud_rate
      : null;

  const cards = [
    {
      title: "Efficacy",
      body: (
        <dl className="space-y-1.5 font-mono text-xs text-ink-muted">
          <div className="flex justify-between gap-2">
            <dt>binary_ap</dt>
            <dd className="text-ink">{formatPct(m.binary_ap)}</dd>
          </div>
          <div className="flex justify-between gap-2">
            <dt>recall@op</dt>
            <dd className="text-ink">{formatPct(m.recall_at_op)}</dd>
          </div>
          <div className="flex justify-between gap-2">
            <dt>precision@op</dt>
            <dd className="text-ink">{formatPct(m.precision_at_op)}</dd>
          </div>
          <div className="flex justify-between gap-2">
            <dt>genuine_fp</dt>
            <dd className="text-ink">{formatPct(m.genuine_fp, 3)}</dd>
          </div>
          <div className="flex justify-between gap-2">
            <dt>authgate p50</dt>
            <dd className="text-ink">
              {m.authgate_ms?.p50 == null ? "—" : `${formatNum(m.authgate_ms.p50, 1)} ms`}
            </dd>
          </div>
        </dl>
      ),
    },
    {
      title: "Fidelity",
      body: (
        <dl className="space-y-1.5 font-mono text-xs text-ink-muted">
          <div className="flex justify-between gap-2">
            <dt>pass</dt>
            <dd className="text-ink">
              {fidelityPass == null ? "—" : fidelityPass ? "true" : "false"}
            </dd>
          </div>
          <div className="flex justify-between gap-2">
            <dt>psi_amount</dt>
            <dd className="text-ink">{formatNum(psiAmount)}</dd>
          </div>
          <div className="flex justify-between gap-2">
            <dt>psi_hour</dt>
            <dd className="text-ink">{formatNum(psiHour)}</dd>
          </div>
          <div className="flex justify-between gap-2">
            <dt>fraud_rate</dt>
            <dd className="text-ink">{formatPct(fraudRate, 2)}</dd>
          </div>
          <div className="flex justify-between gap-2">
            <dt>run_id</dt>
            <dd className="text-ink truncate max-w-[140px]">
              {snapshot.generate.last_run?.run_id ?? "—"}
            </dd>
          </div>
        </dl>
      ),
    },
    {
      title: "Governance",
      body: (
        <div>
          <dl className="space-y-1.5 font-mono text-xs text-ink-muted">
            <div className="flex justify-between gap-2">
              <dt>HITL pending</dt>
              <dd className="text-ink">{snapshot.identify.hitl_pending}</dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt>drafts</dt>
              <dd className="text-ink">{snapshot.defend.drafts_pending}</dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt>retrain queue</dt>
              <dd className="text-ink">{snapshot.evolve.retrain_queue?.length ?? 0}</dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt>catalog_solved</dt>
              <dd className="text-ink">false</dd>
            </div>
          </dl>
          <EthicsChips ethics={snapshot.ethics} />
        </div>
      ),
    },
  ];

  return (
    <section className="mb-8">
      <div className="font-mono uppercase text-ink-faint text-xs tracking-wide mb-3">
        Reports
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {cards.map((c) => (
          <div key={c.title} className="bg-white border border-border rounded-xl p-5">
            <div className="font-mono text-xs font-semibold uppercase tracking-wide text-[#166534] mb-3">
              {c.title}
            </div>
            {c.body}
          </div>
        ))}
      </div>
    </section>
  );
}
