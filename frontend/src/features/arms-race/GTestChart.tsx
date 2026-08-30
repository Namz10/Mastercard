import { useMemo } from "react";
import clsx from "clsx";
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
import type { ArmsRaceViewModel } from "./arms-race-vm";
import { formatPct } from "@/lib/format";

const BASE_BLUE = "#2563EB";
const FEEDBACK_GREEN = "#166534";

export function GTestChart({
  vm,
  pulse,
}: {
  vm: ArmsRaceViewModel;
  pulse?: boolean;
}) {
  const data = useMemo(() => vm.barChart.rows, [vm.barChart.rows]);
  const { family, apDelta, verdict } = vm.barChart;

  return (
    <section
      className={clsx(
        "bg-white border border-gray-200 rounded-xl p-5 transition-shadow",
        pulse && "ring-2 ring-[#166534]/40 ring-offset-2",
      )}
      data-demo="gtest-chart"
    >
      <p className="text-center font-mono text-xs uppercase tracking-wide text-ink-faint mb-4">
        G-TEST: BASE MODEL VS POST FEEDBACK LOOP
      </p>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 12, left: 4, bottom: 0 }} barGap={4} barCategoryGap="20%">
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
            <XAxis dataKey="metric" tick={{ fontSize: 11, fill: "#5c6169" }} axisLine={{ stroke: "#e5e7eb" }} />
            <YAxis
              tickFormatter={(v) => `${Math.round(Number(v) * 100)}%`}
              tick={{ fontSize: 10, fill: "#8b9098" }}
              domain={[0, 1]}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              formatter={(v) => formatPct(typeof v === "number" ? v : Number(v))}
              contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e5e7eb" }}
            />
            <Legend
              wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
              formatter={(value) => <span className="text-ink-muted">{value}</span>}
            />
            <Bar
              dataKey="postFeedback"
              name="Post feedback loop"
              fill={FEEDBACK_GREEN}
              radius={[2, 2, 0, 0]}
              maxBarSize={48}
              className={clsx(pulse && "motion-safe:animate-pulse")}
            />
            <Bar
              dataKey="baseModel"
              name="Base model"
              fill={BASE_BLUE}
              radius={[2, 2, 0, 0]}
              maxBarSize={48}
              className={clsx(pulse && "motion-safe:animate-pulse")}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="text-center font-mono text-xs text-ink-faint mt-4">
        AP delta ({family}): {formatPct(apDelta, 2)} · verdict: {verdict}
      </p>
    </section>
  );
}
