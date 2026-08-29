import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { StatusChip } from "@/components/ui/StatusChip";
import { Table, Td, Th } from "@/components/ui/Table";
import { ErrorState } from "@/components/ui/ErrorState";
import { useHitlQueue, useIdentifyMutations } from "./useIdentify";

export function HitlQueueTable() {
  const { data, isLoading, isError, refetch } = useHitlQueue();
  const { approve, reject, rejectUnsafe } = useIdentifyMutations();

  if (isLoading) return <Spinner label="Loading HITL queue…" />;
  if (isError) return <ErrorState message="Could not load HITL queue." onRetry={() => void refetch()} />;
  if (!data?.count) {
    return <EmptyState title="No candidates yet — enter a topic above to start research." />;
  }

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
        {data.items.map((item, index) => (
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
                  onClick={() => approve.mutate(item.vector_id)}
                  data-demo={index === 0 ? "hitl-approve" : undefined}
                >
                  Approve
                </Button>
                <Button
                  variant="secondary"
                  disabled={reject.isPending}
                  onClick={() => reject.mutate(item.vector_id)}
                >
                  Reject
                </Button>
                <Button
                  variant="danger"
                  disabled={rejectUnsafe.isPending}
                  onClick={() => rejectUnsafe.mutate(item.vector_id)}
                >
                  Unsafe
                </Button>
              </div>
            </Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
