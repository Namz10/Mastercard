import { useState } from "react";
import { Link } from "react-router-dom";
import clsx from "clsx";
import type { RetrainHistoryEntry } from "./retrain-types";
import { formatPct } from "@/lib/format";

function formatWhen(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function RetrainHistory({ history }: { history: RetrainHistoryEntry[] }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="border border-gray-200 rounded-lg bg-white">
      <button
        type="button"
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-surface-sunken/50 rounded-lg"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="text-sm font-semibold text-ink">Retrain history</span>
        <span className="font-mono text-[11px] text-ink-faint">
          {history.length} run{history.length === 1 ? "" : "s"} · {open ? "▲" : "▼"}
        </span>
      </button>

      {open ? (
        <div className="px-4 pb-4 border-t border-border">
          {history.length === 0 ? (
            <p className="text-xs text-ink-faint pt-3">No approved Loop M runs yet.</p>
          ) : (
            <ul className="flex flex-col gap-2 pt-3">
              {history.map((e) => (
                <li
                  key={e.id}
                  className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 rounded-md border border-gray-100 bg-surface-sunken/40 px-3 py-2"
                >
                  <p className="font-mono text-[11px] text-ink-muted">
                    {formatWhen(e.approved_at)} · {e.miss_family} ·{" "}
                    <span className={clsx(e.pass ? "text-[#166534]" : "text-signal-block")}>
                      {e.pass ? "PASS" : "FAIL"}
                    </span>{" "}
                    · ΔAP {e.ap_delta >= 0 ? "+" : ""}
                    {formatPct(e.ap_delta, 2).replace("%", "pp")} · FPR{" "}
                    {e.genuine_fp_ok ? "ok" : "warn"} · catalog_solved:false
                  </p>
                  <Link
                    to="/simulation"
                    className="text-[11px] text-[#166534] hover:underline shrink-0"
                  >
                    Simulation Console
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  );
}
