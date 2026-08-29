import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";

export function ReasonCodes({ features }: { features: string[] | null }) {
  if (!features?.length) {
    return <EmptyState title="Top contributing features appear after scoring." />;
  }

  return (
    <Card title="Top contributing features">
      <ul className="space-y-2">
        {features.slice(0, 12).map((feature, i) => (
          <li key={feature} className="flex gap-3 text-sm">
            <span className="font-mono text-ink-faint w-6 shrink-0">{String(i + 1).padStart(2, "0")}</span>
            <span className="font-mono text-ink-muted">{feature}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
