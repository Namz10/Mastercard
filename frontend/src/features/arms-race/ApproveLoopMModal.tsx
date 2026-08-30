import { useEffect } from "react";
import { Button } from "@/components/ui/Button";
import type { RetrainQueueItem } from "./retrain-types";

export function ApproveLoopMModal({
  open,
  item,
  queueLength,
  pending,
  onCancel,
  onConfirm,
}: {
  open: boolean;
  item: RetrainQueueItem | null;
  queueLength: number;
  pending: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !pending) onCancel();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, pending, onCancel]);

  if (!open || !item) return null;

  const fnNote = item.n_fn_is_npos_proxy
    ? `${item.n_fn.toLocaleString()} n_pos (FN proxy)`
    : item.n_fn_estimated
      ? `≈${item.n_fn.toLocaleString()} estimated FN`
      : `${item.n_fn.toLocaleString()} FN rows`;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40"
      role="dialog"
      aria-modal="true"
      aria-labelledby="approve-loop-m-title"
      onClick={() => {
        if (!pending) onCancel();
      }}
    >
      <div
        className="w-full max-w-md bg-white border border-gray-200 rounded-xl shadow-lg p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="approve-loop-m-title" className="text-base font-semibold text-ink mb-3">
          Approve Loop M retrain
        </h2>

        {queueLength > 1 ? (
          <p className="font-mono text-xs text-[#166534] mb-3 bg-green-50 border border-green-100 rounded px-2 py-1.5">
            Running 1 of {queueLength} — {item.label_family} first
          </p>
        ) : null}

        <p className="text-sm text-ink-muted mb-3">You are approving Loop M retrain on:</p>
        <ul className="space-y-2 text-sm text-ink font-mono bg-surface-sunken border border-border rounded-lg p-3 mb-4">
          <li>
            • miss_family: <strong>{item.label_family}</strong> ({fnNote})
          </li>
          <li>• Extra rows appended to TRAIN COPY ONLY (cap ≤15%)</li>
          <li>• G-test rescored on new seed (48) — not mined from G-test</li>
          <li>
            • catalog_solved will remain <strong>FALSE</strong>
          </li>
          <li>• Genuine FPR must stay within ε=0.02 or run fails</li>
        </ul>

        <p className="text-[11px] text-ink-faint leading-relaxed mb-4">
          Train extras never touch frozen G-test event IDs. Miss family from gdev44 / inner_val —
          not G-test seed 43. Simulation Console may show EVOLVE · Loop M while this runs.
        </p>

        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" disabled={pending} onClick={onCancel}>
            Cancel
          </Button>
          <Button
            type="button"
            disabled={pending}
            className="!bg-[#166534] !text-white hover:!bg-[#14532d]"
            onClick={onConfirm}
            data-demo="approve-loop-m"
            autoFocus
          >
            {pending ? "Running Loop M…" : "I approve — run Loop M"}
          </Button>
        </div>
      </div>
    </div>
  );
}
