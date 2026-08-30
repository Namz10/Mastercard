import { Button } from "@/components/ui/Button";
import { COPY } from "@/lib/copy";
import type { HitlItem } from "@/lib/api-types";
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

  if (items.length === 0) {
    return <p className="text-[13px] text-ink-muted">{COPY.identify.emptyProposed}</p>;
  }

  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div
          key={item.vector_id}
          className="border border-border rounded bg-surface px-4 py-3 flex flex-col gap-2"
        >
          <div className="flex items-start justify-between gap-2">
            <div>
              <div className="font-mono text-[11px] text-ink-faint">
                {COPY.identify.attackId}: {item.technique_id}
              </div>
              <div className="text-[14px] font-medium text-ink">{item.name ?? item.technique_id}</div>
            </div>
          </div>
          {item.source_urls?.length ? (
            <p className="text-[12px] text-ink-muted truncate">{item.source_urls[0]}</p>
          ) : null}
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
        </div>
      ))}
    </div>
  );
}
