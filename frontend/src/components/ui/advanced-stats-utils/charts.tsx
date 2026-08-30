import { useEffect, useId, useState } from "react";
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { cn } from "@/lib/utils";
import { usePrefersReducedMotion } from "@/hooks/usePrefersReducedMotion";

export interface ClippedAreaPoint {
  label: string;
  value: number;
}

export interface ClippedAreaChartProps {
  data: ClippedAreaPoint[];
  valueLabel?: string;
  className?: string;
  height?: number | string;
  yDomain?: [number, number];
  formatValue?: (value: number) => string;
  formatLabel?: (label: string) => string;
}

const chartConfig = {
  value: {
    label: "Recall",
    color: "var(--accent)",
  },
} satisfies ChartConfig;

export function ClippedAreaChart({
  data,
  valueLabel = "Recall",
  className,
  height = "100%",
  yDomain,
  formatValue = (v) => `${v.toFixed(1)}%`,
  formatLabel = (l) => l,
}: ClippedAreaChartProps) {
  const reduced = usePrefersReducedMotion();
  const clipId = useId().replace(/:/g, "");
  const [progress, setProgress] = useState(reduced ? 1 : 0);

  useEffect(() => {
    if (reduced) {
      setProgress(1);
      return;
    }
    const frame = requestAnimationFrame(() => setProgress(1));
    return () => cancelAnimationFrame(frame);
  }, [reduced, data]);

  const domain = yDomain ?? (() => {
    const vals = data.map((d) => d.value);
    const min = Math.min(...vals, 0);
    const max = Math.max(...vals, 100);
    const pad = (max - min) * 0.08 || 4;
    return [Math.max(0, min - pad), Math.min(100, max + pad)] as [number, number];
  })();

  const config: ChartConfig = {
    value: { ...chartConfig.value, label: valueLabel },
  };

  return (
    <div className={cn("relative min-h-0 w-full", className)} style={{ height }}>
      <ChartContainer config={config} className="h-full w-full aspect-auto">
        <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={`fill-${clipId}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.28} />
              <stop offset="100%" stopColor="var(--accent)" stopOpacity={0.02} />
            </linearGradient>
            <clipPath id={`clip-${clipId}`}>
              <rect
                x="0"
                y="0"
                width={`${progress * 100}%`}
                height="100%"
                style={{
                  transition: reduced ? undefined : "width 900ms cubic-bezier(0.22, 1, 0.36, 1)",
                }}
              />
            </clipPath>
          </defs>
          <CartesianGrid stroke="var(--hairline)" vertical={false} />
          <XAxis
            dataKey="label"
            tickLine={false}
            axisLine={false}
            tickMargin={6}
            tick={{ fontSize: 10, fill: "var(--ink-3)", fontFamily: "IBM Plex Mono" }}
            tickFormatter={formatLabel}
          />
          <YAxis
            domain={domain}
            tickLine={false}
            axisLine={false}
            tickMargin={4}
            width={36}
            tick={{ fontSize: 10, fill: "var(--ink-3)", fontFamily: "IBM Plex Mono" }}
            tickFormatter={(v) => `${v}`}
          />
          <ChartTooltip
            cursor={{ stroke: "var(--hairline)", strokeWidth: 1 }}
            content={
              <ChartTooltipContent
                hideLabel
                formatter={(value) => formatValue(Number(value ?? 0))}
              />
            }
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke="var(--ink)"
            strokeWidth={1.75}
            fill={`url(#fill-${clipId})`}
            clipPath={`url(#clip-${clipId})`}
            isAnimationActive={false}
            dot={false}
            activeDot={{ r: 4, fill: "var(--accent)", stroke: "var(--surface-solid)", strokeWidth: 1.5 }}
          />
        </AreaChart>
      </ChartContainer>
    </div>
  );
}
