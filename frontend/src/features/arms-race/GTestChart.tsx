import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import type { LoopMResponse, ScoreResponse } from "@/lib/api-types";
import { formatPct } from "@/lib/format";

function metricRows(staticScore: ScoreResponse | null, loopM: LoopMResponse | null) {
  const staticMetrics = staticScore?.metrics;
  const before = loopM?.metrics?.gtest_before;
  const after = loopM?.metrics?.gtest_after;

  return [
    {
      metric: "Binary AP",
      static: staticMetrics?.binary_ap ?? 0,
      loopM: after?.binary_ap ?? before?.binary_ap ?? 0,
    },
    {
      metric: "Precision",
      static: staticMetrics?.precision_at_op ?? 0,
      loopM: after?.precision_at_op ?? before?.precision_at_op ?? 0,
    },
    {
      metric: "Recall",
      static: staticMetrics?.recall_at_op ?? 0,
      loopM: after?.recall_at_op ?? before?.recall_at_op ?? 0,
    },
  ];
}

export function GTestChart({
  staticScore,
  loopM,
}: {
  staticScore: ScoreResponse | null;
  loopM: LoopMResponse | null;
}) {
  if (!staticScore && !loopM) {
    return <EmptyState title="Run Decisioning score first, then Loop M here." />;
  }

  const data = metricRows(staticScore, loopM);

  return (
    <Card title="G-test: Static vs Loop M">
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="metric" tick={{ fontSize: 11 }} />
            <YAxis tickFormatter={(v) => formatPct(v, 0)} tick={{ fontSize: 10 }} domain={[0, 1]} />
            <Tooltip formatter={(v) => formatPct(typeof v === "number" ? v : Number(v))} />
            <Legend />
            <Bar dataKey="static" name="Static baseline" fill="var(--signal-info)" radius={[3, 3, 0, 0]} />
            <Bar dataKey="loopM" name="Loop M" fill="var(--signal-safe)" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      {loopM?.comparison?.ap_delta != null ? (
        <p className="text-xs font-mono text-ink-muted mt-3">
          AP delta ({loopM.comparison.family}): {formatPct(loopM.comparison.ap_delta, 2)} · verdict:{" "}
          {loopM.comparison.ap_verdict}
        </p>
      ) : null}
    </Card>
  );
}
