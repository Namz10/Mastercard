import { useMemo } from "react";
import {
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
import type { ArmsRaceViewModel } from "./arms-race-vm";
import { StatusChip } from "@/components/ui/StatusChip";

const RED = "#DC2626";
const GREEN = "#166534";
const GRAY = "#8b9098";

function CustomTooltip({
  active,
  payload,
  label,
  gtestSeed,
  trainSeed,
}: {
  active?: boolean;
  payload?: { dataKey: string; value: number; color: string }[];
  label?: string;
  gtestSeed: number;
  trainSeed: number;
}) {
  if (!active || !payload?.length || label === "G2") return null;
  const row = Object.fromEntries(payload.map((p) => [p.dataKey, p.value]));
  return (
    <div className="bg-white border border-gray-200 rounded-lg px-3 py-2 text-xs shadow-sm font-mono">
      <p className="font-semibold text-ink mb-1">{label}</p>
      {row.evasionPct != null ? <p className="text-[#DC2626]">Red evasion: {Number(row.evasionPct).toFixed(0)}%</p> : null}
      {row.prAucPct != null ? <p className="text-[#166534]">Blue PR-AUC: {Number(row.prAucPct).toFixed(0)}%</p> : null}
      {row.genuineFprPct != null ? (
        <p className="text-ink-muted">Genuine FPR: {Number(row.genuineFprPct).toFixed(2)}%</p>
      ) : null}
      <p className="text-ink-faint mt-1">gtest_seed={gtestSeed} · train_seed={trainSeed}</p>
    </div>
  );
}

export function CoEvolutionChart({ vm }: { vm: ArmsRaceViewModel["coEvolution"] }) {
  const plotData = useMemo(
    () =>
      vm.points.map((p) => ({
        ...p,
        evasionPct: p.evasion != null ? p.evasion * 100 : null,
        prAucPct: p.prAuc != null ? p.prAuc * 100 : null,
        genuineFprPct: p.genuineFpr != null ? p.genuineFpr * 100 : null,
      })),
    [vm.points],
  );

  return (
    <section className="bg-white border border-gray-200 rounded-xl p-5">
      <div className="flex flex-col gap-3 mb-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <h2 className="text-sm font-semibold text-ink">Co-evolution across generations</h2>
          <p className="font-mono text-xs text-ink-faint">
            family={vm.family} · gtest_seed={vm.gtestSeed} · train_seed={vm.trainSeed}
          </p>
        </div>
        {vm.pass ? (
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs tabular-nums text-[#166534]">
              +{(vm.apDelta * 100).toFixed(2)}pp AP
            </span>
            <StatusChip status="pass" />
          </div>
        ) : null}
      </div>

      <div className="h-[280px]">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={plotData} margin={{ top: 16, right: 16, left: 8, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="gen"
              tick={({ x, y, payload }) => (
                <text
                  x={x}
                  y={y + 12}
                  textAnchor="middle"
                  fontSize={11}
                  fill={payload.value === "G2" ? "#c9cdc3" : "#5c6169"}
                  fontFamily="IBM Plex Mono, monospace"
                >
                  {payload.value}
                </text>
              )}
              axisLine={{ stroke: "#e5e7eb" }}
            />
            <YAxis
              yAxisId="left"
              orientation="left"
              domain={[0, 100]}
              tickFormatter={(v) => `${v}%`}
              tick={{ fontSize: 10, fill: RED }}
              axisLine={false}
              tickLine={false}
              label={{
                value: "Red evasion rate %",
                angle: -90,
                position: "insideLeft",
                offset: 10,
                style: { fontSize: 10, fill: RED },
              }}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              domain={[0, 100]}
              tickFormatter={(v) => `${v}%`}
              tick={{ fontSize: 10, fill: GREEN }}
              axisLine={false}
              tickLine={false}
              label={{
                value: "Blue PR-AUC",
                angle: 90,
                position: "insideRight",
                offset: 10,
                style: { fontSize: 10, fill: GREEN },
              }}
            />
            <Tooltip
              content={<CustomTooltip gtestSeed={vm.gtestSeed} trainSeed={vm.trainSeed} />}
            />
            <Legend
              wrapperStyle={{ fontSize: 11, paddingTop: 4 }}
              formatter={(value) => <span className="text-ink-muted">{value}</span>}
            />
            <ReferenceLine
              x="G1"
              yAxisId="left"
              stroke="#c9cdc3"
              strokeDasharray="4 4"
              label={{
                value: "Feedback loop retrain",
                position: "insideTopRight",
                fontSize: 10,
                fill: "#8b9098",
              }}
            />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="evasionPct"
              name="Red evasion"
              stroke={RED}
              strokeWidth={2}
              dot={{ r: 4, fill: RED, strokeWidth: 0 }}
              connectNulls={false}
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="prAucPct"
              name="Blue PR-AUC"
              stroke={GREEN}
              strokeWidth={2}
              dot={{ r: 4, fill: GREEN, strokeWidth: 0 }}
              connectNulls={false}
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="genuineFprPct"
              name="Genuine FPR (guardrail)"
              stroke={GRAY}
              strokeWidth={1.5}
              strokeDasharray="5 4"
              dot={false}
              connectNulls={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <p className="text-[11px] text-ink-faint mt-3 leading-relaxed">
        G2+ projected only. v1 demonstrates one feedback loop iteration. catalog_solved remains false. Cat 4 offline.
      </p>
    </section>
  );
}
