import { formatInt, formatNum, formatPct } from "@/lib/format";
import type { LabCounters, LedgerSnippet } from "./lab-types";

function Cell({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-[110px]">
      <div className="font-mono text-[10px] uppercase tracking-wide text-ink-faint mb-0.5">{label}</div>
      <div className="font-mono text-sm text-ink tabular-nums">{value}</div>
    </div>
  );
}

export function CountersStrip({
  counters,
  ledgerSnippets,
}: {
  counters: LabCounters;
  ledgerSnippets: LedgerSnippet[];
}) {
  return (
    <div className="bg-surface border border-border rounded p-4">
      <div className="flex flex-wrap gap-x-6 gap-y-3">
        <Cell label="events" value={formatInt(counters.events)} />
        <Cell label="rows exported" value={formatInt(counters.rowsExported)} />
        <Cell label="fraud_rate" value={formatPct(counters.fraudRate, 2)} />
        <Cell
          label="fidelity.pass"
          value={counters.fidelityPass == null ? "—" : counters.fidelityPass ? "true" : "false"}
        />
        <Cell label="genuine_FPR" value={formatPct(counters.genuineFpr, 3)} />
        <Cell
          label="authgate_ms_p50"
          value={counters.authgateMsP50 == null ? "—" : formatNum(counters.authgateMsP50, 0)}
        />
        <Cell label="model_freeze_id" value={counters.modelFreezeId ?? "—"} />
      </div>

      {ledgerSnippets.length > 0 ? (
        <div className="mt-3 pt-3 border-t border-border">
          <div className="font-mono text-[10px] uppercase tracking-wide text-ink-faint mb-2">
            Last ledger events
          </div>
          <div className="flex flex-wrap gap-2">
            {ledgerSnippets.map((s, i) => (
              <span
                key={`${s.lifecycle_stage}-${s.party_id}-${i}`}
                className="font-mono text-[11px] px-2 py-1 rounded border border-border bg-surface-sunken text-ink-muted"
              >
                {s.lifecycle_stage} · {s.party_id}
              </span>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
