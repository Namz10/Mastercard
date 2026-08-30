import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";

const ACTION_COLORS: Record<string, string> = {
  allow: "var(--signal-safe)",
  notify: "var(--signal-watch)",
  step_up: "var(--signal-watch)",
  hold: "var(--signal-block)",
  decline: "var(--signal-block)",
  mule_credit_restrict: "var(--signal-watch)",
};

export function ActionHistogram({ histogram }: { histogram: Record<string, number> | null }) {
  if (!histogram || Object.keys(histogram).length === 0) {
    return <EmptyState title="Action histogram appears after scoring." />;
  }

  const data = Object.entries(histogram).map(([action, count]) => ({ action, count }));

  return (
    <Card title="Brake action histogram">
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ left: 8, right: 8 }}>
            <XAxis type="number" tick={{ fontSize: 11 }} />
            <YAxis type="category" dataKey="action" width={100} tick={{ fontSize: 10, fontFamily: "IBM Plex Mono" }} />
            <Tooltip />
            <Bar dataKey="count" radius={[0, 3, 3, 0]}>
              {data.map((entry) => (
                <Cell key={entry.action} fill={ACTION_COLORS[entry.action] ?? "var(--signal-idle)"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
