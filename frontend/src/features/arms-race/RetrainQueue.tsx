import type { RetrainQueueItem } from "./retrain-types";
import { Button } from "@/components/ui/Button";

function fnLabel(item: RetrainQueueItem): string {
  if (item.n_fn_is_npos_proxy) return `n_pos≈${item.n_fn.toLocaleString()}`;
  if (item.n_fn_estimated) return `est. FN≈${item.n_fn.toLocaleString()}`;
  return `n_fn=${item.n_fn.toLocaleString()}`;
}

export function RetrainQueue({
  queue,
  onRemove,
  onMove,
  onAddSelected,
  canAdd,
}: {
  queue: RetrainQueueItem[];
  onRemove: (id: string) => void;
  onMove: (id: string, direction: "up" | "down") => void;
  onAddSelected: () => void;
  canAdd: boolean;
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 flex flex-col gap-3 min-h-[200px]">
      <div className="flex items-center justify-between gap-2">
        <h3 className="font-mono text-[10px] uppercase tracking-wide text-ink-faint">
          Queue ({queue.length})
        </h3>
        <Button
          type="button"
          variant="secondary"
          className="!py-1 !px-2 text-xs"
          disabled={!canAdd}
          onClick={onAddSelected}
          data-demo="add-to-retrain-queue"
        >
          Add to retrain queue
        </Button>
      </div>

      {queue.length === 0 ? (
        <div className="border border-dashed border-border rounded-lg p-5 text-center flex-1 flex flex-col items-center justify-center">
          <p className="text-sm text-ink-muted">No families queued.</p>
          <p className="text-xs text-ink-faint mt-1 max-w-xs">
            Score a run or select misses from the inbox.
          </p>
        </div>
      ) : (
        <ul className="flex flex-col gap-2 max-h-[340px] overflow-y-auto pr-1">
          {queue.map((item, index) => (
            <li
              key={item.id}
              className="rounded-lg border border-gray-200 bg-white p-3"
              data-demo={index === 0 ? "retrain-queue-head" : undefined}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-ink">
                    {item.name}{" "}
                    <span className="font-mono text-ink-faint text-xs">({item.label_family})</span>
                  </p>
                  <p className="font-mono text-[11px] text-ink-muted mt-1">
                    {fnLabel(item)} · cap will apply at 15% train rows
                  </p>
                  <p className="font-mono text-[10px] text-ink-faint mt-0.5">
                    train_seed=42 · gtest_seed=48 · slice=gdev44 · order #{index + 1}
                  </p>
                </div>
                <div className="flex flex-col gap-1 shrink-0">
                  <button
                    type="button"
                    className="px-1.5 py-0.5 text-[10px] font-mono text-ink-muted border border-border rounded hover:bg-surface-sunken disabled:opacity-30"
                    disabled={index === 0}
                    onClick={() => onMove(item.id, "up")}
                    aria-label="Move up"
                  >
                    ▲
                  </button>
                  <button
                    type="button"
                    className="px-1.5 py-0.5 text-[10px] font-mono text-ink-muted border border-border rounded hover:bg-surface-sunken disabled:opacity-30"
                    disabled={index === queue.length - 1}
                    onClick={() => onMove(item.id, "down")}
                    aria-label="Move down"
                  >
                    ▼
                  </button>
                </div>
              </div>
              <div className="mt-2">
                <Button
                  type="button"
                  variant="secondary"
                  className="!py-1 !px-2 text-xs"
                  onClick={() => onRemove(item.id)}
                >
                  Remove
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
