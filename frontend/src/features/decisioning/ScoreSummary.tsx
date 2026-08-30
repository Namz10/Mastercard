import { Card } from "@/components/ui/Card";
import type { ScoreMetrics } from "@/lib/api-types";
import { formatPct } from "@/lib/format";

export function ScoreSummary({ metrics }: { metrics: ScoreMetrics | null }) {
  if (!metrics) {
    return (
      <Card title="Score summary">
        <p className="text-sm text-ink-muted">Fit and score a generate run to see metrics.</p>
      </Card>
    );
  }

  const items = [
    { label: "Precision @ OP", value: formatPct(metrics.precision_at_op) },
    { label: "Recall @ OP", value: formatPct(metrics.recall_at_op) },
    { label: "F1 @ OP", value: formatPct(metrics.f1_at_op) },
    { label: "Binary AP", value: formatPct(metrics.binary_ap) },
    { label: "Genuine FP", value: formatPct(metrics.genuine_fp) },
    { label: "Eval rows", value: String(metrics.n_eval) },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      {items.map((item) => (
        <Card key={item.label} title={item.label}>
          <div className="text-lg font-mono font-medium">{item.value}</div>
        </Card>
      ))}
    </div>
  );
}
