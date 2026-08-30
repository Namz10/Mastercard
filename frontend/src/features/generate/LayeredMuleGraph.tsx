import type { GenerateRunResponse } from "@/lib/api-types";
import { FAMILY_LABEL } from "@/lib/format";

const LAYERS = ["Originators", "Mule", "Aggregation", "Cash-out"] as const;

export function LayeredMuleGraph({ run }: { run: GenerateRunResponse | null }) {
  const mule = run?.counts_by_label_family?.mule ?? 0;
  const fanIn = run?.fidelity?.mule_fan_in_median;
  const families = Object.entries(run?.counts_by_label_family ?? {}).filter(([k]) => k !== "normal");

  return (
    <div className="flex-1 min-h-0 border border-border rounded bg-surface flex flex-col">
      <div className="px-3 py-2 border-b border-border font-mono text-[11px] uppercase text-ink-faint">
        Correspondent chain
      </div>
      <svg viewBox="0 0 627 320" className="flex-1 w-full min-h-[180px]">
        {LAYERS.map((label, i) => (
          <g key={label}>
            <line x1={80 + i * 140} y1={28} x2={80 + i * 140} y2={300} stroke="#E2DFD6" />
            <text x={80 + i * 140} y={18} textAnchor="middle" fontSize={11} fill="#6B7367" fontFamily="IBM Plex Mono">
              {label}
            </text>
          </g>
        ))}
        {families.slice(0, 8).map(([family], i) => {
          const x = 80 + (i % 4) * 140;
          const y = 70 + Math.floor(i / 4) * 90;
          const muleNode = family === "mule";
          return (
            <g key={family}>
              {i > 0 ? (
                <line
                  x1={80 + ((i - 1) % 4) * 140 + 24}
                  y1={70 + Math.floor((i - 1) / 4) * 90 + 14}
                  x2={x - 24}
                  y2={y + 14}
                  stroke="#191C19"
                  strokeOpacity={0.7}
                  strokeWidth={1.5}
                />
              ) : null}
              <rect
                x={x - 24}
                y={y}
                width={48}
                height={28}
                rx={6}
                fill={muleNode ? "#E9F0E9" : "#FFFFFF"}
                stroke={muleNode ? "#3E6B4F" : "#191C19"}
              />
              <text
                x={x}
                y={y + 18}
                textAnchor="middle"
                fontSize={10}
                fill="#191C19"
                fontFamily="IBM Plex Mono"
              >
                {FAMILY_LABEL[family] ?? family}
              </text>
            </g>
          );
        })}
      </svg>
      <p className="px-3 py-2 font-mono text-[11px] text-ink-faint border-t border-border">
        {fanIn != null
          ? `Median mule fan-in ${fanIn.toFixed(1)} · ${mule} mule accounts · computed, not copied from the recipe.`
          : "Originators → mule → aggregation → cash-out. Edges appear when layering injects."}
      </p>
    </div>
  );
}
