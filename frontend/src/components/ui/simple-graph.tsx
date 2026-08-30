import { useEffect, useId, useMemo, useRef, useState } from "react";
import { usePrefersReducedMotion } from "@/hooks/usePrefersReducedMotion";
import { cn } from "@/lib/utils";

export type DataPoint = { value: number; label?: string };

export type SimpleGraphProps = {
  data: DataPoint[];
  lineColor?: string;
  dotColor?: string;
  width?: string | number;
  height?: number;
  animationDuration?: number;
  showGrid?: boolean;
  gridStyle?: "solid" | "dashed" | "dotted";
  gridLines?: "vertical" | "horizontal" | "both";
  gridLineThickness?: number;
  showDots?: boolean;
  dotSize?: number;
  dotHoverGlow?: boolean;
  curved?: boolean;
  gradientFade?: boolean;
  graphLineThickness?: number;
  calculatePercentageDifference?: boolean;
  animateOnScroll?: boolean;
  animateOnce?: boolean;
  className?: string;
};

const SAGE = "#3E6B4F";
const HAIRLINE = "#E2DFD6";

function buildPath(
  points: { x: number; y: number }[],
  curved: boolean,
): string {
  if (points.length === 0) return "";
  if (points.length === 1) return `M ${points[0].x} ${points[0].y}`;
  if (!curved) {
    return points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
  }
  let d = `M ${points[0].x} ${points[0].y}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i];
    const p1 = points[i + 1];
    const cx = (p0.x + p1.x) / 2;
    d += ` C ${cx} ${p0.y}, ${cx} ${p1.y}, ${p1.x} ${p1.y}`;
  }
  return d;
}

export function SimpleGraph({
  data,
  lineColor = SAGE,
  dotColor = SAGE,
  width = "100%",
  height = 300,
  animationDuration = 0.16,
  showGrid = true,
  gridStyle = "dashed",
  gridLines = "horizontal",
  gridLineThickness = 1,
  showDots = true,
  dotSize = 5,
  dotHoverGlow = false,
  curved = true,
  gradientFade = false,
  graphLineThickness = 2,
  calculatePercentageDifference = false,
  animateOnScroll = false,
  animateOnce = true,
  className,
}: SimpleGraphProps) {
  const reducedMotion = usePrefersReducedMotion();
  const wrapRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(!animateOnScroll);
  const [drawn, setDrawn] = useState(reducedMotion);
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  const gradId = useId();

  useEffect(() => {
    if (!animateOnScroll || reducedMotion) {
      setVisible(true);
      return;
    }
    const el = wrapRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          if (animateOnce) obs.disconnect();
        } else if (!animateOnce) {
          setVisible(false);
        }
      },
      { threshold: 0.2 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [animateOnScroll, animateOnce, reducedMotion]);

  useEffect(() => {
    if (!visible || reducedMotion) {
      setDrawn(true);
      return;
    }
    setDrawn(false);
    const ms = Math.max(0, animationDuration * 1000);
    const t = window.setTimeout(() => setDrawn(true), ms);
    return () => window.clearTimeout(t);
  }, [visible, reducedMotion, animationDuration, data]);

  const layout = useMemo(() => {
    const pad = { top: 16, right: 12, bottom: 28, left: 36 };
    const w = 400;
    const h = height;
    const innerW = w - pad.left - pad.right;
    const innerH = h - pad.top - pad.bottom;
    const values = data.map((d) => d.value);
    const minV = Math.min(0, ...values);
    const maxV = Math.max(...values, 1);
    const span = maxV - minV || 1;
    const pts = data.map((d, i) => {
      const x = pad.left + (data.length <= 1 ? innerW / 2 : (i / (data.length - 1)) * innerW);
      const y = pad.top + innerH - ((d.value - minV) / span) * innerH;
      return { x, y, ...d };
    });
    return { w, h, pad, pts, minV, maxV, innerH };
  }, [data, height]);

  const path = buildPath(layout.pts, curved);
  const areaPath =
    gradientFade && layout.pts.length > 1
      ? `${path} L ${layout.pts[layout.pts.length - 1].x} ${layout.h - layout.pad.bottom} L ${layout.pts[0].x} ${layout.h - layout.pad.bottom} Z`
      : "";

  const gridDash = gridStyle === "dashed" ? "4 4" : gridStyle === "dotted" ? "2 3" : undefined;
  const yTicks = 4;

  return (
    <div ref={wrapRef} className={cn("relative font-mono", className)} style={{ width, height }}>
      <svg viewBox={`0 0 ${layout.w} ${layout.h}`} className="h-full w-full" role="img" aria-hidden={data.length === 0}>
        {gradientFade ? (
          <defs>
            <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={lineColor} stopOpacity={0.12} />
              <stop offset="100%" stopColor={lineColor} stopOpacity={0} />
            </linearGradient>
          </defs>
        ) : null}

        {showGrid && (gridLines === "horizontal" || gridLines === "both")
          ? Array.from({ length: yTicks + 1 }, (_, i) => {
              const y = layout.pad.top + (i / yTicks) * layout.innerH;
              return (
                <line
                  key={`h-${i}`}
                  x1={layout.pad.left}
                  y1={y}
                  x2={layout.w - layout.pad.right}
                  y2={y}
                  stroke={HAIRLINE}
                  strokeWidth={gridLineThickness}
                  strokeDasharray={gridDash}
                />
              );
            })
          : null}

        {showGrid && (gridLines === "vertical" || gridLines === "both")
          ? layout.pts.map((p, i) => (
              <line
                key={`v-${i}`}
                x1={p.x}
                y1={layout.pad.top}
                x2={p.x}
                y2={layout.h - layout.pad.bottom}
                stroke={HAIRLINE}
                strokeWidth={gridLineThickness}
                strokeDasharray={gridDash}
              />
            ))
          : null}

        {areaPath ? <path d={areaPath} fill={`url(#${gradId})`} /> : null}

        {path ? (
          <path
            d={path}
            fill="none"
            stroke={lineColor}
            strokeWidth={graphLineThickness}
            strokeLinecap="round"
            strokeLinejoin="round"
            pathLength={1}
            style={
              reducedMotion
                ? undefined
                : {
                    strokeDasharray: 1,
                    strokeDashoffset: drawn ? 0 : 1,
                    transition: `stroke-dashoffset ${animationDuration}s ease-out`,
                  }
            }
          />
        ) : null}

        {showDots
          ? layout.pts.map((p, i) => (
              <g
                key={i}
                onMouseEnter={() => setHoverIdx(i)}
                onMouseLeave={() => setHoverIdx(null)}
              >
                {dotHoverGlow && hoverIdx === i ? (
                  <circle cx={p.x} cy={p.y} r={dotSize + 4} fill={dotColor} opacity={0.15} />
                ) : null}
                <circle
                  cx={p.x}
                  cy={p.y}
                  r={dotSize / 2}
                  fill="#FFFFFF"
                  stroke={dotColor}
                  strokeWidth={1.5}
                />
              </g>
            ))
          : null}

        {layout.pts.map((p, i) =>
          p.label ? (
            <text
              key={`lbl-${i}`}
              x={p.x}
              y={layout.h - 8}
              textAnchor="middle"
              fontSize={9}
              fill="#6B7367"
            >
              {p.label}
            </text>
          ) : null,
        )}
      </svg>

      {hoverIdx != null && layout.pts[hoverIdx] ? (
        <div
          className="pointer-events-none absolute z-10 rounded border border-border bg-paper-1 px-2 py-1 text-[11px] text-ink shadow-drawer"
          style={{
            left: `${(layout.pts[hoverIdx].x / layout.w) * 100}%`,
            top: `${(layout.pts[hoverIdx].y / layout.h) * 100}%`,
            transform: "translate(-50%, -120%)",
          }}
        >
          {calculatePercentageDifference && hoverIdx > 0 ? (
            <span>
              {(
                ((layout.pts[hoverIdx].value - layout.pts[hoverIdx - 1].value) /
                  Math.max(1, layout.pts[hoverIdx - 1].value)) *
                100
              ).toFixed(1)}
              %
            </span>
          ) : (
            <span className="font-tabular">{layout.pts[hoverIdx].value.toLocaleString("en-IN")}</span>
          )}
        </div>
      ) : null}

      {data.length === 0 ? (
        <div className="absolute inset-0 flex items-center justify-center text-[12px] text-ink-faint">No data</div>
      ) : null}
    </div>
  );
}
