import { useMemo } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ScoreMetrics } from "@/lib/api-types";
import { ChartFooterStrip } from "@/components/ui/ChartFooterStrip";
import { buildRecallFprCurve, opPoint } from "./recall-fpr-data";

const CHAMPION_BLUE = "#2563EB";
const BASELINE_GRAY = "#9ca3af";

function RecallTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { dataKey: string; value: number; payload: { fprLabel: string } }[];
}) {
  if (!active || !payload?.length) return null;
  const row = payload[0]?.payload;
  const champion = payload.find((p) => p.dataKey === "championRecall")?.value;
  const baseline = payload.find((p) => p.dataKey === "baselineRecall")?.value;
  return (
    <div className="bg-white border border-gray-200 rounded-lg px-3 py-2 text-xs shadow-sm">
      <p className="font-mono text-ink-faint mb-1">Genuine FPR {row?.fprLabel}%</p>
      {champion != null ? (
        <p className="text-[#2563EB] font-medium">Champion recall: {champion.toFixed(1)}%</p>
      ) : null}
      {baseline != null ? (
        <p className="text-ink-muted">Stage 1 baseline: {baseline.toFixed(1)}%</p>
      ) : null}
    </div>
  );
}

export function RecallFprCurve({ metrics }: { metrics: ScoreMetrics }) {
  const data = useMemo(() => buildRecallFprCurve(metrics), [metrics]);
  const op = useMemo(() => opPoint(metrics), [metrics]);

  const yMin = Math.max(0, Math.floor(Math.min(...data.map((d) => d.baselineRecall)) / 5) * 5 - 5);
  const yMax = Math.min(100, Math.ceil(Math.max(...data.map((d) => d.championRecall)) / 5) * 5 + 5);

  const onePctPoint = data.find((d) => d.fprLabel === "1");

  return (
    <section className="bg-white border border-gray-200 rounded-xl p-5 md:p-6">
      <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-3 mb-1">
        <div>
          <h2 className="text-base font-semibold text-ink">Recall under a genuine false-positive cap</h2>
          <p className="text-xs text-ink-muted mt-1">
            Internal holdout world · not production · not external transfer
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-4 text-xs font-mono shrink-0">
          <span className="flex items-center gap-1.5 text-ink">
            <span className="w-3 h-0.5 bg-[#2563EB] rounded" />
            Champion (family-targeted refit)
          </span>
          <span className="flex items-center gap-1.5 text-ink-muted">
            <span className="w-3 h-0.5 bg-gray-400 rounded border border-dashed border-gray-400" />
            Stage 1 baseline
          </span>
        </div>
      </div>

      <div className="h-72 mt-4 relative">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 12, right: 16, left: 52, bottom: 24 }}>
            <defs>
              <linearGradient id="championFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={CHAMPION_BLUE} stopOpacity={0.12} />
                <stop offset="100%" stopColor={CHAMPION_BLUE} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="4 4" stroke="#e5e7eb" vertical={false} />
            <XAxis
              dataKey="fprLabel"
              tick={{ fontSize: 11, fill: "#5c6169" }}
              axisLine={{ stroke: "#e5e7eb" }}
              label={{
                value: "Genuine FPR (%)",
                position: "insideBottom",
                offset: -4,
                style: { fontSize: 11, fill: "#8b9098" },
              }}
            />
            <YAxis
              width={40}
              domain={[yMin, yMax]}
              allowDecimals={false}
              tickCount={6}
              tickFormatter={(v) => String(Math.round(Number(v)))}
              tick={{ fontSize: 10, fill: "#8b9098" }}
              axisLine={false}
              tickLine={false}
              label={{
                value: "Fraud recall (%)",
                angle: -90,
                position: "left",
                offset: 12,
                style: { fontSize: 11, fill: "#5c6169", textAnchor: "middle" },
              }}
            />
            <Tooltip content={<RecallTooltip />} />
            <Legend wrapperStyle={{ display: "none" }} />
            <Area
              type="monotone"
              dataKey="championRecall"
              stroke="none"
              fill="url(#championFill)"
              legendType="none"
            />
            <Line
              type="monotone"
              dataKey="baselineRecall"
              name="Stage 1 baseline"
              stroke={BASELINE_GRAY}
              strokeWidth={2}
              dot={{ r: 4, fill: "#fff", stroke: BASELINE_GRAY, strokeWidth: 2 }}
              activeDot={{ r: 5 }}
            />
            <Line
              type="monotone"
              dataKey="championRecall"
              name="Champion"
              stroke={CHAMPION_BLUE}
              strokeWidth={2.5}
              dot={{ r: 4, fill: CHAMPION_BLUE, strokeWidth: 0 }}
              activeDot={{ r: 5 }}
            />
            {onePctPoint ? (
              <ReferenceLine
                x="1"
                stroke="#c9cdc3"
                strokeDasharray="4 4"
                label={{
                  value: `${onePctPoint.championRecall.toFixed(1)}% recall @ 1% genuine FPR`,
                  position: "insideTopLeft",
                  fontSize: 10,
                  fill: "#5c6169",
                }}
              />
            ) : null}
          </ComposedChart>
        </ResponsiveContainer>

        <div className="absolute bottom-10 left-12 max-w-[200px] rounded-lg border border-gray-200 bg-white/95 px-2.5 py-2 text-[10px] leading-snug shadow-sm">
          <p className="font-semibold text-ink">Selected operating region</p>
          <p className="text-ink-muted font-mono mt-0.5">
            {op.recallPct.toFixed(1)}% recall
            <br />
            genuine FPR ≤ {op.fprPct.toFixed(2)}%
          </p>
        </div>
      </div>

      <ChartFooterStrip
        columns={[
          {
            index: "01",
            title: "Why this chart",
            body: "A detector that flags almost every genuine payment can show high recall. The curve asks: how much fraud remains caught when genuine FPR is capped.",
          },
          {
            index: "02",
            title: "How the threshold is chosen",
            body: `The ${(op.fprPct).toFixed(2)}% cap threshold is selected on training inner_val. The holdout world is scored once. Thresholds are not searched on the test labels.`,
          },
          {
            index: "03",
            title: "Protocol freeze (separate from the curve)",
            body: `inner_val threshold ${op.threshold.toFixed(3)} → holdout eval fold. ${op.recallPct.toFixed(1)}% recall at ${op.fprPct.toFixed(3)}% genuine FPR on this run.`,
          },
        ]}
      />

      <p className="text-[10px] text-ink-faint mt-4 font-mono">
        Internal simulator holdout. Do not label as accuracy or real-world performance.
      </p>
    </section>
  );
}
