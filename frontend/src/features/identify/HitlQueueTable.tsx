/** Quarantined GFF 2026 — off nav. Proof-only lab. Do not restore to chrome. */
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { StatusChip } from "@/components/ui/StatusChip";
import { Table, Td, Th } from "@/components/ui/Table";
import { ErrorState } from "@/components/ui/ErrorState";
import { useHitlQueue, useIdentifyMutations } from "./useIdentify";
import { useIdentifySession } from "./useIdentifySession";
import type { HitlItem } from "@/lib/api-types";
import { pendingHitlItems } from "@/lib/hitl-dedupe";

function recordFromItem(
  item: HitlItem,
  decision: "accepted" | "rejected",
): { vector_id: string; name: string; decision: "accepted" | "rejected" } {
  return {
    vector_id: item.vector_id,
    name: item.name ?? item.vector_id,
    decision,
  };
}

export function HitlQueueTable() {
  const { session, recordDecision } = useIdentifySession();
  const { data, isLoading, isError, refetch } = useHitlQueue();
  const { approve, reject, rejectUnsafe } = useIdentifyMutations();

  const pending = pendingHitlItems(data?.items ?? []);
  const decidedIds = new Set(session.decisions.map((d) => d.vector_id));
  const decidedForThisTopic = session.decisions;

  if (isLoading) return <Spinner label="Loading HITL queue…" />;
  if (isError) return <ErrorState message="Could not load HITL queue." onRetry={() => void refetch()} />;
  if (pending.length === 0 && decidedForThisTopic.length === 0) {
    return <EmptyState title="No candidates yet — enter a topic above to start research." />;
  }

  const pendingRows = pending.filter((c) => !decidedIds.has(c.vector_id));

  return (
    <Table>
      <thead>
        <tr>
          <Th mono>vector_id</Th>
          <Th>Technique</Th>
          <Th>Tier</Th>
          <Th>Confidence</Th>
          <Th>Mode</Th>
          <Th>Actions</Th>
        </tr>
      </thead>
      <tbody className="divide-y divide-border">
        {pendingRows.map((item, index) => (
          <tr key={item.vector_id}>
            <Td mono>{item.vector_id}</Td>
            <Td>
              <div className="font-medium">{item.name}</div>
              <div className="font-mono text-xs text-ink-faint">{item.technique_id}</div>
            </Td>
            <Td mono>{item.tier_badges?.[0] ?? "—"}</Td>
            <Td>
              <StatusChip status={item.confidence_level ?? "reported_unverified"} />
            </Td>
            <Td mono>{item.generate_mode ?? "—"}</Td>
            <Td>
              <div className="flex gap-2">
                <Button
                  variant="primary"
                  disabled={approve.isPending}
                  onClick={() =>
                    approve.mutate(item.vector_id, {
                      onSuccess: () => recordDecision(recordFromItem(item, "accepted")),
                    })
                  }
                  data-demo={index === 0 ? "hitl-approve" : undefined}
                >
                  Approve
                </Button>
                <Button
                  variant="secondary"
                  disabled={reject.isPending}
                  onClick={() =>
                    reject.mutate(item.vector_id, {
                      onSuccess: () => recordDecision(recordFromItem(item, "rejected")),
                    })
                  }
                >
                  Reject
                </Button>
                <Button
                  variant="danger"
                  disabled={rejectUnsafe.isPending}
                  onClick={() =>
                    rejectUnsafe.mutate(item.vector_id, {
                      onSuccess: () => recordDecision(recordFromItem(item, "rejected")),
                    })
                  }
                >
                  Unsafe
                </Button>
              </div>
            </Td>
          </tr>
        ))}
        {decidedForThisTopic.map((d) => (
          <tr key={d.vector_id}>
            <Td mono className="text-ink-muted">
              {d.vector_id}
            </Td>
            <Td colSpan={4}>
              <div className="font-medium text-ink-muted">{d.name}</div>
            </Td>
            <Td>
              <span
                className={`text-xs font-mono ${d.decision === "accepted" ? "text-signal-safe" : "text-signal-block"}`}
              >
                {d.name} was {d.decision === "accepted" ? "accepted" : "rejected"}
              </span>
            </Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
