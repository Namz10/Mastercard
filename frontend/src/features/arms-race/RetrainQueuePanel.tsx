import { Button } from "@/components/ui/Button";
import { MissInbox } from "./MissInbox";
import { RetrainQueue } from "./RetrainQueue";
import { ApproveLoopMModal } from "./ApproveLoopMModal";
import { RetrainHistory } from "./RetrainHistory";
import type { MissRow, RetrainHistoryEntry, RetrainQueueItem } from "./retrain-types";

export function RetrainQueuePanel({
  misses,
  selectedIds,
  queuedFamilies,
  queue,
  history,
  pending,
  modalOpen,
  modalItem,
  error,
  onToggle,
  onToggleAll,
  onAddSelected,
  onRemove,
  onMove,
  onOpenApprove,
  onCancelApprove,
  onConfirmApprove,
  canAdd,
}: {
  misses: MissRow[];
  selectedIds: Set<string>;
  queuedFamilies: Set<string>;
  queue: RetrainQueueItem[];
  history: RetrainHistoryEntry[];
  pending: boolean;
  modalOpen: boolean;
  modalItem: RetrainQueueItem | null;
  error: string | null;
  onToggle: (id: string) => void;
  onToggleAll: (ids: string[]) => void;
  onAddSelected: () => void;
  onRemove: (id: string) => void;
  onMove: (id: string, direction: "up" | "down") => void;
  onOpenApprove: () => void;
  onCancelApprove: () => void;
  onConfirmApprove: () => void;
  canAdd: boolean;
}) {
  return (
    <section className="space-y-4" id="retrain-queue">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-ink">Retrain queue</h2>
          <p className="text-xs text-ink-muted mt-1">
            Missed threats → user approval → Loop M. One family at a time. catalog_solved remains
            false.
          </p>
        </div>
        <Button
          className={
            queue.length ? "!bg-[#166534] !text-white hover:!bg-[#14532d]" : undefined
          }
          variant={queue.length ? "primary" : "secondary"}
          disabled={!queue.length || pending}
          onClick={onOpenApprove}
          data-demo="open-approve-loop-m"
        >
          {pending ? "Running Loop M…" : "Approve & run Loop M"}
        </Button>
      </div>

      {error ? (
        <div
          className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-signal-block"
          role="alert"
        >
          {error}
        </div>
      ) : null}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <MissInbox
          rows={misses}
          selectedIds={selectedIds}
          queuedFamilies={queuedFamilies}
          onToggle={onToggle}
          onToggleAll={onToggleAll}
        />
        <RetrainQueue
          queue={queue}
          onRemove={onRemove}
          onMove={onMove}
          onAddSelected={onAddSelected}
          canAdd={canAdd}
        />
      </div>

      <div className="font-mono text-[11px] text-ink-faint space-y-1 border border-border rounded p-3 bg-surface-sunken">
        <p>catalog_solved: false · Train extras never touch frozen G-test event IDs</p>
        <p>Miss family from gdev44 / inner_val — not G-test seed 43</p>
        <p>Cat 4: offline · Oracle Guard · not public API</p>
        <p>When Loop M starts, Simulation Console may show EVOLVE · Loop M.</p>
      </div>

      <RetrainHistory history={history} />

      <ApproveLoopMModal
        open={modalOpen}
        item={modalItem}
        queueLength={queue.length}
        pending={pending}
        onCancel={onCancelApprove}
        onConfirm={onConfirmApprove}
      />
    </section>
  );
}
