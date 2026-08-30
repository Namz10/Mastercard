import { useMemo } from "react";
import clsx from "clsx";
import type { GenerateRunResponse } from "@/lib/api-types";
import { FAMILY_LABEL } from "@/lib/format";
import { usePrefersReducedMotion } from "@/hooks/usePrefersReducedMotion";

const LAYERS = ["Originators", "Mule", "Aggregation", "Cash-out"] as const;

const LAYER_X = [72, 232, 392, 552];
const LAYER_MAP: Record<string, number> = {
  app_fraud: 0,
  ato: 0,
  identity_burst: 1,
  mule: 1,
  invoice_fraud: 2,
  normal: 3,
};

const LAYER_EDGES: [string, string][] = [
  ["app_fraud", "identity_burst"],
  ["ato", "mule"],
  ["identity_burst", "invoice_fraud"],
  ["mule", "invoice_fraud"],
  ["invoice_fraud", "mule"],
];

function nodePos(family: string, indexInLayer: number, layerCount: number): { x: number; y: number } {
  const layer = LAYER_MAP[family] ?? 0;
  const x = LAYER_X[layer];
  const spread = 56;
  const centerY = 168;
  const offset = (indexInLayer - (layerCount - 1) / 2) * spread;
  return { x, y: centerY + offset };
}

function curvePath(x1: number, y1: number, x2: number, y2: number): string {
  const mid = (x1 + x2) / 2;
  return `M ${x1} ${y1} C ${mid} ${y1}, ${mid} ${y2}, ${x2} ${y2}`;
}

export function LayeredMuleGraph({
  run,
  running,
}: {
  run: GenerateRunResponse | null;
  running?: boolean;
}) {
  const reducedMotion = usePrefersReducedMotion();
  const mule = run?.counts_by_label_family?.mule ?? 0;
  const fanIn = run?.fidelity?.mule_fan_in_median;
  const families = Object.entries(run?.counts_by_label_family ?? {}).filter(([k]) => k !== "normal");

  const layout = useMemo(() => {
    const byLayer: Record<number, string[]> = { 0: [], 1: [], 2: [], 3: [] };
    for (const [family] of families) {
      const layer = LAYER_MAP[family] ?? 0;
      byLayer[layer].push(family);
    }
    const positions: Record<string, { x: number; y: number }> = {};
    for (const layer of [0, 1, 2, 3]) {
      const list = byLayer[layer];
      list.forEach((family, i) => {
        positions[family] = nodePos(family, i, list.length);
      });
    }
    return { positions, byLayer };
  }, [families]);

  const edges = useMemo(() => {
    const present = new Set(families.map(([f]) => f));
    return LAYER_EDGES.filter(([a, b]) => present.has(a) && present.has(b));
  }, [families]);

  const hasData = families.length > 0;

  return (
    <div
      className={clsx(
        "bento-panel workspace-card-lift flex-1 min-h-[320px] lg:min-h-[340px] flex flex-col overflow-hidden",
        hasData && "mule-graph-live",
      )}
      data-demo="mule-graph"
    >
      <div className="px-4 py-2 border-b border-border/60 flex items-center justify-between">
        <div>
          <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint">Mule chain</span>
          <p className="text-[11px] text-ink-faint mt-0.5 hidden sm:block">Money flow · the punchline</p>
        </div>
        {fanIn != null ? (
          <span className="font-mono text-[10px] text-sage-700 bg-sage-100/80 px-2 py-0.5 rounded-full border border-sage-600/20">
            fan-in {fanIn.toFixed(1)}
          </span>
        ) : null}
      </div>

      <div className="relative flex-1 min-h-[280px] mule-graph-canvas">
        <svg viewBox="0 0 624 340" className="w-full h-full min-h-[280px]" preserveAspectRatio="xMidYMid meet">
          <defs>
            <filter id="mule-glow" x="-40%" y="-40%" width="180%" height="180%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            <linearGradient id="mule-column-fade" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#3E6B4F" stopOpacity="0" />
              <stop offset="12%" stopColor="#3E6B4F" stopOpacity="0.12" />
              <stop offset="88%" stopColor="#3E6B4F" stopOpacity="0.12" />
              <stop offset="100%" stopColor="#3E6B4F" stopOpacity="0" />
            </linearGradient>
          </defs>

          {LAYERS.map((label, i) => (
            <g key={label}>
              <line x1={LAYER_X[i]} y1={36} x2={LAYER_X[i]} y2={304} stroke="url(#mule-column-fade)" strokeWidth={1} />
              <text
                x={LAYER_X[i]}
                y={24}
                textAnchor="middle"
                fontSize={10}
                fill="#3E6B4F"
                fontFamily="IBM Plex Mono"
                fontWeight={500}
                letterSpacing="0.1em"
              >
                {label.toUpperCase()}
              </text>
            </g>
          ))}

          {hasData ? (
            <>
              {edges.map(([from, to]) => {
                const p1 = layout.positions[from];
                const p2 = layout.positions[to];
                if (!p1 || !p2) return null;
                const active = from === "mule" || to === "mule";
                const pathD = curvePath(p1.x + 52, p1.y, p2.x - 52, p2.y);
                const pathId = `mule-edge-${from}-${to}`;
                return (
                  <g key={`${from}-${to}`}>
                    <path
                      id={pathId}
                      d={pathD}
                      fill="none"
                      stroke={active ? "#3E6B4F" : "#191C19"}
                      strokeOpacity={active ? 0.5 : 0.18}
                      strokeWidth={active ? 2.5 : 1.5}
                      strokeDasharray={active ? undefined : "4 3"}
                    />
                    {active && !reducedMotion ? (
                      <circle r="3.5" fill="#3E6B4F" opacity={0.85}>
                        <animateMotion dur="2.8s" repeatCount="indefinite" path={pathD} />
                      </circle>
                    ) : null}
                  </g>
                );
              })}

              {families.map(([family, count]) => {
                const pos = layout.positions[family];
                if (!pos) return null;
                const muleNode = family === "mule";
                const label = FAMILY_LABEL[family] ?? family;
                const w = Math.max(88, label.length * 7.2 + 24);
                return (
                  <g key={family} filter={muleNode ? "url(#mule-glow)" : undefined}>
                    <rect
                      x={pos.x - w / 2}
                      y={pos.y - 18}
                      width={w}
                      height={36}
                      rx={10}
                      fill={muleNode ? "#E9F0E9" : "#FFFFFF"}
                      stroke={muleNode ? "#3E6B4F" : "rgba(25,28,25,0.18)"}
                      strokeWidth={muleNode ? 2 : 1}
                    />
                    <text
                      x={pos.x}
                      y={pos.y + 1}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fontSize={11}
                      fill="#191C19"
                      fontFamily="IBM Plex Mono"
                      fontWeight={muleNode ? 600 : 400}
                    >
                      {label}
                    </text>
                    <text
                      x={pos.x}
                      y={pos.y + 28}
                      textAnchor="middle"
                      fontSize={9}
                      fill="#6B7367"
                      fontFamily="IBM Plex Mono"
                    >
                      {count.toLocaleString("en-IN")}
                    </text>
                  </g>
                );
              })}
            </>
          ) : (
            <g>
              {LAYERS.map((label, i) => (
                <rect
                  key={label}
                  x={LAYER_X[i] - 40}
                  y={148}
                  width={80}
                  height={32}
                  rx={8}
                  fill="#FAFAFB"
                  stroke="#E4E6EE"
                  strokeDasharray="4 3"
                />
              ))}
              <text x={312} y={168} textAnchor="middle" fontSize={12} fill="#6B7367" fontFamily="IBM Plex Sans">
                {running ? "Layering injects money flow…" : "Chain appears after simulate"}
              </text>
            </g>
          )}
        </svg>
      </div>

      <p className="px-4 py-2 font-mono text-[10px] text-ink-faint border-t border-border/60 leading-relaxed">
        {fanIn != null
          ? `${mule.toLocaleString("en-IN")} mule accounts · median fan-in ${fanIn.toFixed(1)} · computed, not copied from recipe`
          : "Originators → mule → aggregation → cash-out"}
      </p>
    </div>
  );
}
