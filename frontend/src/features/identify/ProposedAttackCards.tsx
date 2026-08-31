import { useCallback, useMemo, useState } from "react";
import { Button } from "@/components/ui/Button";
import { COPY } from "@/lib/copy";
import { ApiError } from "@/lib/api-client";
import type { HitlItem } from "@/lib/api-types";
import { dedupeHitlItems, pendingHitlItems } from "@/lib/hitl-dedupe";
import { useIdentifyMutations } from "./useIdentify";
import { approveAttack, useSessionSnapshot } from "@/lib/session-store";

export function ProposedAttackCards({
  items,
  onApproved,
}: {
  items: HitlItem[];
  onApproved: () => void;
}) {
  const session = useSessionSnapshot();
  const { approve, reject, rejectUnsafe } = useIdentifyMutations();
  const [approvingIds, setApprovingIds] = useState<Set<string>>(() => new Set());
  const [optimisticCatalog, setOptimisticCatalog] = useState<Set<string>>(() => new Set());

  const approvedTechniques = useMemo(
    () => new Set(session.identify.approved.map((a) => a.techniqueId.toUpperCase())),
    [session.identify.approved],
  );

  const unique = dedupeHitlItems(items);
  const pending = pendingHitlItems(unique).filter((item) => {
    const tid = (item.technique_id ?? "").toUpperCase();
    if (approvedTechniques.has(tid)) return false;
    if (optimisticCatalog.has(item.vector_id)) return false;
    return true;
  });
  const catalog = unique.filter(
    (i) =>
      i.disposition === "in_catalog" ||
      optimisticCatalog.has(i.vector_id) ||
      approvedTechniques.has((i.technique_id ?? "").toUpperCase()),
  );

  const handleApprove = (item: HitlItem) => {
    const id = item.vector_id;
    setApprovingIds((prev) => new Set(prev).add(id));
    approve.mutate(id, {
      onSuccess: () => {
        approveAttack({
          id: item.vector_id,
          techniqueId: item.technique_id,
          name: item.name ?? item.technique_id,
        });
        setOptimisticCatalog((prev) => new Set(prev).add(id));
        onApproved();
      },
      onError: (err) => {
        if (err instanceof ApiError && err.status === 409) {
          approveAttack({
            id: item.vector_id,
            techniqueId: item.technique_id,
            name: item.name ?? item.technique_id,
          });
          setOptimisticCatalog((prev) => new Set(prev).add(id));
          onApproved();
        }
      },
      onSettled: () => {
        setApprovingIds((prev) => {
          const next = new Set(prev);
          next.delete(id);
          return next;
        });
      },
    });
  };

  const lockActions = useCallback(
    (id: string) => approvingIds.has(id) || approve.isPending,
    [approvingIds, approve.isPending],
  );

  if (unique.length === 0) {
    return (
      <div className="bento-panel p-8 text-center">
        <p className="text-[16px] font-medium text-ink">{COPY.identify.emptyProposed}</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {pending.length === 0 && catalog.length > 0 ? (
        <p className="text-[12px] text-ink-faint">{COPY.identify.catalogContext}</p>
      ) : null}
      {pending.map((item) => (
        <AttackCard key={item.vector_id} item={item}>
          <div className="flex items-center gap-3 flex-wrap">
            <Button
              variant="primary"
              disabled={lockActions(item.vector_id)}
              onClick={() => handleApprove(item)}
              data-demo="approve-attack"
            >
              {COPY.identify.add}
            </Button>
            <button
              type="button"
              className="text-[12px] text-ink-faint hover:text-ink disabled:opacity-40"
              disabled={lockActions(item.vector_id)}
              onClick={() => reject.mutate(item.vector_id)}
            >
              {COPY.identify.dismiss}
            </button>
            <button
              type="button"
              className="text-[12px] text-ink-faint hover:text-ink disabled:opacity-40"
              title="Not safe to simulate."
              disabled={lockActions(item.vector_id)}
              onClick={() => rejectUnsafe.mutate(item.vector_id)}
            >
              {COPY.identify.unsafe}
            </button>
          </div>
        </AttackCard>
      ))}
      {catalog.length > 0 ? (
        <div className="space-y-2 pt-1 border-t border-border">
          {pending.length > 0 ? (
            <p className="text-[11px] font-mono uppercase text-ink-faint pt-1">{COPY.identify.catalogContext}</p>
          ) : null}
          {catalog.map((item) => (
            <AttackCard key={item.vector_id} item={item} muted>
              <span
                className="inline-flex items-center h-7 px-2 rounded-full border border-sage-600/30 bg-sage-100 text-[11px] font-mono uppercase text-sage-600"
                data-demo="in-catalog"
              >
                {COPY.identify.inCatalog}
              </span>
            </AttackCard>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function AttackCard({
  item,
  children,
  muted = false,
}: {
  item: HitlItem;
  children: React.ReactNode;
  muted?: boolean;
}) {
  const evidence = [
    ...(item.source_urls ?? []),
    item.corroboration_type,
    item.confidence_level,
  ].filter((v): v is string => Boolean(v));

  return (
    <div
      className={
        muted
          ? "bento-panel px-4 py-3 flex flex-col gap-2 opacity-90"
          : "bento-panel px-4 py-3 flex flex-col gap-2"
      }
    >
      <div>
        <div className="font-mono text-[11px] text-ink-faint">
          {COPY.identify.attackId}: {item.technique_id}
        </div>
        <div className="text-[14px] font-medium text-ink">{item.name ?? item.technique_id}</div>
      </div>
      {evidence.length ? (
        <ul className="text-[12px] text-ink-muted space-y-0.5">
          {evidence.slice(0, 4).map((line) => (
            <li key={line} className="truncate border-l border-border pl-2">
              {line}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-[12px] text-ink-faint">No source URLs on this proposal.</p>
      )}
      {children}
    </div>
  );
}
