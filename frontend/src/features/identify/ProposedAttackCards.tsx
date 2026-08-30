import type { ReactNode } from "react";
import { Button } from "@/components/ui/Button";
import { COPY } from "@/lib/copy";
import type { HitlItem } from "@/lib/api-types";
import { dedupeHitlItems, pendingHitlItems } from "@/lib/hitl-dedupe";
import { useIdentifyMutations } from "./useIdentify";
import { approveAttack } from "@/lib/session-store";

export function ProposedAttackCards({
  items,
  onApproved,
}: {
  items: HitlItem[];
  onApproved: () => void;
}) {
  const { approve, reject, rejectUnsafe } = useIdentifyMutations();
  const unique = dedupeHitlItems(items);
  const pending = pendingHitlItems(unique);
  const catalog = unique.filter((i) => i.disposition === "in_catalog");

  if (unique.length === 0) {
    return <p className="text-[13px] text-ink-muted">{COPY.identify.emptyProposed}</p>;
  }

  return (
    <div className="space-y-3">
      {pending.length === 0 && catalog.length > 0 ? (
        <p className="text-[12px] text-ink-faint">{COPY.identify.catalogContext}</p>
      ) : null}
      {pending.map((item) => (
        <AttackCard key={item.vector_id} item={item}>
          <div className="flex gap-2">
            <Button
              variant="primary"
              disabled={approve.isPending}
              onClick={() =>
                approve.mutate(item.vector_id, {
                  onSuccess: () => {
                    approveAttack({
                      id: item.vector_id,
                      techniqueId: item.technique_id,
                      name: item.name ?? item.technique_id,
                    });
                    onApproved();
                  },
                })
              }
            >
              {COPY.identify.add}
            </Button>
            <Button variant="secondary" onClick={() => reject.mutate(item.vector_id)}>
              {COPY.identify.dismiss}
            </Button>
            <Button
              variant="secondary"
              title="Not safe to simulate."
              onClick={() => rejectUnsafe.mutate(item.vector_id)}
            >
              {COPY.identify.unsafe}
            </Button>
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
              <span className="inline-flex items-center h-7 px-2 rounded-full border border-sage-600/30 bg-sage-100 text-[11px] font-mono uppercase text-sage-600">
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
  children: ReactNode;
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
