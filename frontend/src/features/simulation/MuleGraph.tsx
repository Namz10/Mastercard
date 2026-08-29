import type { GenerateRunResponse } from "@/lib/api-types";
import { EmptyState } from "@/components/ui/EmptyState";

interface Node {
  id: string;
  x: number;
  y: number;
  r: number;
}

function layoutNodes(counts: Record<string, number>): { nodes: Node[]; edges: [number, number][] } {
  const families = Object.entries(counts).filter(([k]) => k !== "normal");
  const n = Math.max(families.length, 3);
  const cx = 160;
  const cy = 120;
  const radius = 70;

  const nodes: Node[] = families.map(([family, count], i) => {
    const angle = (i / n) * Math.PI * 2 - Math.PI / 2;
    return {
      id: family,
      x: cx + Math.cos(angle) * radius,
      y: cy + Math.sin(angle) * radius,
      r: Math.min(24, 8 + Math.sqrt(count)),
    };
  });

  const hub: Node = { id: "mule_hub", x: cx, y: cy, r: 14 };
  const allNodes = [hub, ...nodes];
  const edges = nodes.map((_, i) => [0, i + 1] as [number, number]);

  return { nodes: allNodes, edges };
}

export function MuleGraph({ run }: { run: GenerateRunResponse | null }) {
  if (!run) {
    return <EmptyState title="Mule graph appears after a population run." />;
  }

  const { nodes, edges } = layoutNodes(run.counts_by_label_family ?? {});
  const fanIn = run.fidelity?.mule_fan_in_median;

  return (
    <div>
      <h3 className="font-mono text-xs uppercase text-ink-faint mb-3 tracking-wide">Mule graph</h3>
      <svg viewBox="0 0 320 240" className="w-full border border-border rounded bg-surface-sunken">
        {edges.map(([from, to], i) => {
          const a = nodes[from];
          const b = nodes[to];
          return (
            <line
              key={i}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke="var(--border-strong)"
              strokeWidth={1}
            />
          );
        })}
        {nodes.map((node) => (
          <g key={node.id}>
            <circle cx={node.x} cy={node.y} r={node.r} fill="var(--surface)" stroke="var(--ink-muted)" />
            <text
              x={node.x}
              y={node.y + node.r + 12}
              textAnchor="middle"
              fontSize={9}
              fill="var(--ink-faint)"
              fontFamily="IBM Plex Mono, monospace"
            >
              {node.id === "mule_hub" ? "hub" : node.id.slice(0, 8)}
            </text>
          </g>
        ))}
      </svg>
      {fanIn != null ? (
        <p className="text-xs font-mono text-ink-muted mt-2">median fan-in: {fanIn.toFixed(1)}</p>
      ) : null}
    </div>
  );
}
