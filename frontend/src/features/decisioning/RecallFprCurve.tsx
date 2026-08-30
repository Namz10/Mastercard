import { useMemo } from "react";
import {
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ScoreMetrics } from "@/lib/api-types";
import { COPY } from "@/lib/copy";
import { buildRecallFprCurve, opPoint } from "./recall-fpr-data";

export function RecallFprCurve({
  metrics,
  before,
}: {
  metrics: ScoreMetrics;
  before?: ScoreMetrics | null;
}) {
  const data = useMemo(() => buildRecallFprCurve(metrics, before), [metrics, before]);
  const op = useMemo(() => opPoint(metrics), [metrics]);
  const hasBefore = Boolean(before && data.some((d) => d.beforeRecall != null));

  return (
    <section className="h-full min-h-0 flex flex-col border border-border rounded bg-surface">
      <div className="px-4 pt-3 pb-1">
        <h2 className="text-[14px] font-medium text-ink">{COPY.defend.chartTitle}</h2>
        <p className="text-[12px] text-ink-faint">{COPY.defend.chartSubtitle}</p>
      </div>
      <div className="flex-1 min-h-[280px] px-2">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 16, right: 16, left: 8, bottom: 8 }}>
            <CartesianGrid stroke="#E2DFD6" vertical={false} />
            <XAxis
              dataKey="fprPct"
              type="number"
              scale="log"
              domain={[0.02, 5]}
              ticks={[0.05, 0.1, 0.5, 1, 5]}
              tick={{ fontSize: 11, fill: "#6B7367", fontFamily: "IBM Plex Mono" }}
              tickFormatter={(v) => String(v)}
              label={{ value: "Genuine FPR (%)", position: "insideBottom", offset: -4, fontSize: 11, fill: "#6B7367" }}
            />
            <YAxis
              domain={[80, 100]}
              tick={{ fontSize: 11, fill: "#6B7367", fontFamily: "IBM Plex Mono" }}
              tickFormatter={(v) => String(v)}
            />
            <Tooltip
              contentStyle={{ border: "1px solid #E2DFD6", borderRadius: 4, boxShadow: "none", fontSize: 12 }}
              formatter={(value: number, name: string) => [`${value.toFixed(1)}%`, name]}
              labelFormatter={(label) => `Genuine FPR ${label}%`}
            />
            {hasBefore ? (
              <Line
                type="monotone"
                dataKey="beforeRecall"
                name={COPY.defend.seriesDetector}
                stroke="#55606B"
                strokeWidth={2}
                strokeDasharray="4 4"
                dot={false}
              />
            ) : null}
            <Line
              type="monotone"
              dataKey="recall"
              name={hasBefore ? COPY.defend.seriesAfterRetrain : COPY.defend.seriesDetector}
              stroke="#191C19"
              strokeWidth={2}
              dot={false}
            />
            <ReferenceDot x={Math.max(0.02, op.fprPct)} y={op.recallPct} r={6} fill="#3E6B4F" stroke="#F7F5F0" strokeWidth={1.5} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <div className="px-4 pb-3">
        <div className="font-mono text-[48px] leading-none text-ink font-tabular">
          {op.recallPct.toFixed(1)}%
        </div>
        <p className="text-[13px] text-ink-muted mt-1">
          {COPY.defend.op(op.recallPct.toFixed(1), op.fprPct.toFixed(3))}
        </p>
        {!hasBefore ? (
          <p className="text-[11px] text-ink-faint mt-1">No pre-retrain series on this run</p>
        ) : null}
      </div>
    </section>
  );
}
