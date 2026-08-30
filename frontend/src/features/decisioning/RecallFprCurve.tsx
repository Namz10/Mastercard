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
import { buildRecallFprCurve, opPoint, recallYDomain } from "./recall-fpr-data";

export function RecallFprCurve({
  metrics,
  before,
  scoring,
  hasBefore: hasBeforeProp,
}: {
  metrics: ScoreMetrics | null;
  before?: ScoreMetrics | null;
  scoring?: boolean;
  hasBefore?: boolean;
}) {
  const data = useMemo(
    () =>
      metrics
        ? buildRecallFprCurve(metrics, before)
        : [
            { fprLabel: "0.05", fprPct: 0.05, recall: 0 },
            { fprLabel: "0.1", fprPct: 0.1, recall: 0 },
            { fprLabel: "0.5", fprPct: 0.5, recall: 0 },
            { fprLabel: "1", fprPct: 1, recall: 0 },
            { fprLabel: "5", fprPct: 5, recall: 0 },
          ],
    [metrics, before],
  );
  const op = metrics ? opPoint(metrics) : null;
  const hasBefore = hasBeforeProp ?? Boolean(before && data.some((d) => d.beforeRecall != null));
  const yDomain = useMemo(() => recallYDomain(data), [data]);

  return (
    <section className="bento-panel workspace-card-lift h-full min-h-[420px] flex flex-col" data-demo="recall-fpr-curve">
      <div className="px-4 py-2.5 flex items-start justify-between gap-3 border-b border-border/60">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint">{COPY.defend.chartSubtitle}</p>
          <h2 className="font-serif text-[18px] font-medium text-ink tracking-tight mt-0.5">{COPY.defend.chartTitle}</h2>
        </div>
        {hasBefore ? (
          <div className="flex flex-wrap items-center gap-3 shrink-0 pt-0.5">
            <span className="inline-flex items-center gap-1.5 text-[11px] text-ink-muted">
              <span className="w-5 h-0.5 bg-slate-500 rounded-full border border-dashed border-slate-400" aria-hidden />
              {COPY.defend.seriesDetector}
            </span>
            <span className="inline-flex items-center gap-1.5 text-[11px] text-ink">
              <span className="w-5 h-0.5 bg-ink rounded-full" aria-hidden />
              {COPY.defend.seriesAfterRetrain}
            </span>
          </div>
        ) : null}
      </div>
      <div className="flex-1 min-h-[360px] px-2 py-1">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 20, right: 20, left: 4, bottom: 12 }}>
            <CartesianGrid stroke="#E4E6EE" vertical={false} />
            <XAxis
              dataKey="fprPct"
              type="number"
              scale="log"
              domain={[0.04, 1.2]}
              ticks={[0.05, 0.1, 0.5, 1]}
              tick={{ fontSize: 11, fill: "#6B7367", fontFamily: "IBM Plex Mono" }}
              tickFormatter={(v) => String(v)}
              label={{ value: "Genuine FPR (%)", position: "insideBottom", offset: -4, fontSize: 11, fill: "#6B7367" }}
            />
            <YAxis
              domain={yDomain}
              tick={{ fontSize: 11, fill: "#6B7367", fontFamily: "IBM Plex Mono" }}
              tickFormatter={(v) => String(v)}
              label={{ value: "Recall (%)", angle: -90, position: "insideLeft", offset: 8, fontSize: 11, fill: "#6B7367" }}
            />
            <Tooltip
              isAnimationActive={false}
              allowEscapeViewBox={{ x: false, y: false }}
              contentStyle={{
                border: "1px solid #E4E6EE",
                borderRadius: 8,
                boxShadow: "none",
                fontSize: 12,
                background: "#FFFFFF",
              }}
              formatter={(value, name) => [`${Number(value ?? 0).toFixed(1)}%`, String(name)]}
              labelFormatter={(label) => `Genuine FPR ${label}%`}
            />
            {hasBefore ? (
              <Line
                type="monotone"
                dataKey="beforeRecall"
                name={COPY.defend.seriesDetector}
                stroke="#55606B"
                strokeWidth={2}
                strokeDasharray="5 4"
                dot={{ r: 5, fill: "#55606B", strokeWidth: 0 }}
                isAnimationActive={false}
              />
            ) : null}
            <Line
              type="monotone"
              dataKey="recall"
              name={hasBefore ? COPY.defend.seriesAfterRetrain : COPY.defend.seriesDetector}
              stroke="#191C19"
              strokeWidth={2.5}
              dot={{ r: 5, fill: "#191C19", strokeWidth: 0 }}
              isAnimationActive={false}
            />
            {data.map((point) =>
              metrics ? (
                <ReferenceDot
                  key={point.fprLabel}
                  x={point.fprPct}
                  y={point.recall}
                  r={4}
                  fill="#FFFFFF"
                  stroke="#3E6B4F"
                  strokeWidth={1.5}
                  label={{
                    value: point.fprLabel,
                    position: "bottom",
                    fontSize: 9,
                    fill: "#6B7367",
                    fontFamily: "IBM Plex Mono",
                  }}
                />
              ) : null,
            )}
            {op ? (
              <ReferenceDot
                x={Math.max(0.02, op.fprPct)}
                y={op.recallPct}
                r={8}
                fill="#3E6B4F"
                stroke="#FFFFFF"
                strokeWidth={2}
                label={{
                  value: "OP",
                  position: "top",
                  fontSize: 10,
                  fill: "#3E6B4F",
                  fontWeight: 600,
                  fontFamily: "IBM Plex Mono",
                }}
              />
            ) : null}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <div className="px-4 pb-3 border-t border-border/40 pt-2.5">
        {op ? (
          <p className="text-[13px] text-ink">{COPY.defend.op(op.recallPct.toFixed(2), op.fprPct.toFixed(3))}</p>
        ) : (
          <p className="text-[13px] font-mono text-ink-faint">
            {scoring ? `${COPY.defend.scoring}…` : COPY.defend.empty}
          </p>
        )}
      </div>
    </section>
  );
}
