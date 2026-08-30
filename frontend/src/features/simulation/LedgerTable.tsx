import { StatusChip } from "@/components/ui/StatusChip";
import { Table, Td, Th } from "@/components/ui/Table";
import { EmptyState } from "@/components/ui/EmptyState";
import type { GenerateRunResponse } from "@/lib/api-types";
import { formatInt } from "@/lib/format";

export function LedgerTable({ run }: { run: GenerateRunResponse | null }) {
  if (!run) {
    return <EmptyState title="No generated ledger yet — run population or canary above." />;
  }

  const rows = Object.entries(run.counts_by_label_family ?? {}).sort((a, b) => b[1] - a[1]);
  const pass = run.fidelity?.pass;

  return (
    <div>
      <div className="flex items-center gap-3 mb-3">
        <h3 className="font-mono text-xs uppercase text-ink-faint tracking-wide">Synthetic ledger</h3>
        <StatusChip status={pass ? "pass" : "fail"} />
        <span className="font-mono text-xs text-ink-faint">{run.run_id}</span>
      </div>
      <div className="text-xs text-ink-muted mb-3 space-y-1 font-mono">
        <div>events: {formatInt(run.event_count)} · mode: {run.mode}</div>
        {run.fidelity?.fraud_rate != null ? (
          <div>fraud_rate: {(run.fidelity.fraud_rate * 100).toFixed(2)}%</div>
        ) : null}
        {run.fidelity?.mule_fan_in_median != null ? (
          <div>mule_fan_in_median: {run.fidelity.mule_fan_in_median.toFixed(1)}</div>
        ) : null}
      </div>
      <Table>
        <thead>
          <tr>
            <Th mono>label_family</Th>
            <Th mono>count</Th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([family, count]) => (
            <tr key={family}>
              <Td mono>{family}</Td>
              <Td mono>{formatInt(count)}</Td>
            </tr>
          ))}
        </tbody>
      </Table>
    </div>
  );
}
