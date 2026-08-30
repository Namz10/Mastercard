import { Link } from "react-router-dom";
import clsx from "clsx";
import type { MissRow } from "./retrain-types";
import { formatPct } from "@/lib/format";

function fnLabel(row: MissRow): string {
  if (row.n_fn_is_npos_proxy) return `n_pos≈${row.n_fn.toLocaleString()}`;
  if (row.n_fn_estimated) return `est. FN≈${row.n_fn.toLocaleString()}`;
  return `n_fn=${row.n_fn.toLocaleString()}`;
}

export function MissInbox({
  rows,
  selectedIds,
  onToggle,
  onToggleAll,
  queuedFamilies,
}: {
  rows: MissRow[];
  selectedIds: Set<string>;
  onToggle: (id: string) => void;
  onToggleAll: (ids: string[]) => void;
  queuedFamilies: Set<string>;
}) {
  const families = [...new Set(rows.map((r) => r.label_family))];
  const totalFn = rows.reduce((s, r) => s + r.n_fn, 0);
  const allIds = rows.map((r) => r.id);
  const allSelected = allIds.length > 0 && allIds.every((id) => selectedIds.has(id));

  if (rows.length === 0) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-4">
        <h3 className="font-mono text-[10px] uppercase tracking-wide text-ink-faint mb-3">
          Miss inbox
        </h3>
        <div className="border border-dashed border-border rounded-lg p-5 text-center">
          <p className="text-sm text-ink-muted">No misses yet.</p>
          <p className="text-xs text-ink-faint mt-1">
            Fit and score a run on Decisioning — inbox fills from score_run FN estimates.
          </p>
        </div>
      </div>
    );
  }

  const grouped = new Map<string, MissRow[]>();
  for (const row of rows) {
    const list = grouped.get(row.label_family) ?? [];
    list.push(row);
    grouped.set(row.label_family, list);
  }

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <h3 className="font-mono text-[10px] uppercase tracking-wide text-ink-faint">Miss inbox</h3>
        <button
          type="button"
          className="text-[11px] font-mono text-ink-muted hover:text-ink underline-offset-2 hover:underline"
          onClick={() => onToggleAll(allSelected ? [] : allIds)}
        >
          {allSelected ? "Clear" : "Select all"}
        </button>
      </div>

      <p className="font-mono text-[11px] text-ink-faint">
        {families.length} families · {totalFn.toLocaleString()} total FN rows
        <span className="text-ink-faint/80"> (n_pos≈ / estimated FN)</span>
      </p>

      <ul className="flex flex-col gap-3 max-h-[340px] overflow-y-auto pr-1">
        {[...grouped.entries()].map(([family, familyRows]) => (
          <li key={family}>
            <p className="font-mono text-[10px] uppercase tracking-wide text-ink-faint mb-1.5">
              {family}
            </p>
            <ul className="flex flex-col gap-2">
              {familyRows.map((row) => {
                const checked = selectedIds.has(row.id);
                const inQueue = queuedFamilies.has(row.label_family);
                return (
                  <li
                    key={row.id}
                    className={clsx(
                      "rounded-lg border bg-white p-3 transition-colors",
                      checked ? "border-[#166534]/40 bg-green-50/40" : "border-gray-200",
                    )}
                  >
                    <label className="flex gap-2.5 cursor-pointer">
                      <input
                        type="checkbox"
                        className="mt-1 accent-[#166534]"
                        checked={checked}
                        onChange={() => onToggle(row.id)}
                        disabled={inQueue}
                      />
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-sm font-medium text-ink">
                            {row.technique_id} · {row.name}
                          </span>
                          {inQueue ? (
                            <span className="inline-flex px-1.5 py-0.5 rounded border border-[#166534]/30 bg-green-50 font-mono text-[9px] uppercase tracking-wide text-[#166534]">
                              In retrain queue
                            </span>
                          ) : null}
                        </div>
                        <p className="font-mono text-[11px] text-ink-muted mt-1">
                          family={row.label_family} · {fnLabel(row)} · evasion=
                          {formatPct(row.evasion_pct, 0)} · detected_by=AuthGate score_run
                        </p>
                        <p className="font-mono text-[10px] text-ink-faint mt-0.5">
                          atlas status: {row.atlas_status} · last_seen: {row.last_seen ?? "—"}
                        </p>
                        <div className="flex flex-wrap gap-3 mt-2">
                          <Link
                            to="/decisioning"
                            className="text-[11px] text-[#166534] hover:underline"
                            onClick={(e) => e.stopPropagation()}
                          >
                            View in Decisioning
                          </Link>
                          <Link
                            to="/"
                            className="text-[11px] text-[#166534] hover:underline"
                            onClick={(e) => e.stopPropagation()}
                          >
                            View in Threat Map
                          </Link>
                        </div>
                      </div>
                    </label>
                  </li>
                );
              })}
            </ul>
          </li>
        ))}
      </ul>
    </div>
  );
}
