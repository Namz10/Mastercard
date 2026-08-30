import { useCallback, useMemo, useState } from "react";
import { usePersistedState } from "@/lib/usePersistedState";
import { STORAGE_KEYS } from "@/lib/storage-keys";
import { useDecisioningState } from "@/features/decisioning/useDecisioningState";
import { useLatestRun } from "@/lib/latest-run-context";
import { deriveMissRowsFromScore } from "./deriveMissRows";
import type { MissRow, RetrainHistoryEntry, RetrainQueueItem } from "./retrain-types";

export function useRetrainQueue() {
  const { score } = useDecisioningState();
  const { lastScore } = useLatestRun();
  const scoreSource = score ?? lastScore;

  const [queue, setQueue] = usePersistedState<RetrainQueueItem[]>(STORAGE_KEYS.retrainQueue, []);
  const [history, setHistory] = usePersistedState<RetrainHistoryEntry[]>(
    STORAGE_KEYS.retrainHistory,
    [],
  );
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set());

  const missRows = useMemo(() => deriveMissRowsFromScore(scoreSource), [scoreSource]);

  const queuedFamilies = useMemo(
    () => new Set(queue.map((q) => q.label_family)),
    [queue],
  );

  const canAdd = useMemo(() => {
    for (const id of selectedIds) {
      const row = missRows.find((r) => r.id === id);
      if (row && !queuedFamilies.has(row.label_family)) return true;
    }
    return false;
  }, [selectedIds, missRows, queuedFamilies]);

  const toggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const toggleAll = useCallback((ids: string[]) => {
    setSelectedIds(ids.length ? new Set(ids) : new Set());
  }, []);

  const addMisses = useCallback(
    (rows: MissRow[]) => {
      if (rows.length === 0) return;
      setQueue((prev) => {
        const existing = new Set(prev.map((p) => p.label_family));
        const additions: RetrainQueueItem[] = [];
        for (const row of rows) {
          if (existing.has(row.label_family)) continue;
          existing.add(row.label_family);
          additions.push({
            id: `queue:${row.label_family}:${Date.now()}`,
            label_family: row.label_family,
            technique_id: row.technique_id,
            name: row.name,
            n_fn: row.n_fn,
            n_fn_estimated: row.n_fn_estimated,
            n_fn_is_npos_proxy: row.n_fn_is_npos_proxy,
            added_at: new Date().toISOString(),
            approved: false,
          });
        }
        return additions.length ? [...prev, ...additions] : prev;
      });
    },
    [setQueue],
  );

  const addSelected = useCallback(() => {
    const rows = missRows.filter(
      (r) => selectedIds.has(r.id) && !queuedFamilies.has(r.label_family),
    );
    addMisses(rows);
    setSelectedIds(new Set());
  }, [missRows, selectedIds, queuedFamilies, addMisses]);

  const removeFromQueue = useCallback(
    (id: string) => {
      setQueue((prev) => prev.filter((q) => q.id !== id));
    },
    [setQueue],
  );

  const moveQueue = useCallback(
    (id: string, direction: "up" | "down") => {
      setQueue((prev) => {
        const idx = prev.findIndex((q) => q.id === id);
        if (idx < 0) return prev;
        const target = direction === "up" ? idx - 1 : idx + 1;
        if (target < 0 || target >= prev.length) return prev;
        const next = [...prev];
        const [item] = next.splice(idx, 1);
        next.splice(target, 0, item);
        return next;
      });
    },
    [setQueue],
  );

  /** After successful Loop M: drop first queue item and append history. */
  const completeFirstAsHistory = useCallback(
    (entry: Omit<RetrainHistoryEntry, "id" | "catalog_solved">) => {
      setQueue((prev) => prev.slice(1));
      setHistory((prev) => [
        {
          ...entry,
          id: `hist:${entry.run_id}:${entry.miss_family}:${Date.now()}`,
          catalog_solved: false,
        },
        ...prev,
      ]);
    },
    [setQueue, setHistory],
  );

  return {
    missRows,
    selectedIds,
    queue,
    history,
    queuedFamilies,
    canAdd,
    toggleSelect,
    toggleAll,
    addSelected,
    addMisses,
    removeFromQueue,
    moveQueue,
    completeFirstAsHistory,
    hasScore: scoreSource != null,
  };
}
