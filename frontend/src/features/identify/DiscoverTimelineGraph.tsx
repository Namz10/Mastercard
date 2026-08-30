import { useMemo } from "react";
import { SimpleGraph } from "@/components/ui/simple-graph";
import { buildDiscoverTimeline } from "@/lib/graph-series";
import type { LogLine } from "./useDiscoverStream";

export function DiscoverTimelineGraph({
  lines,
  running = false,
}: {
  lines: LogLine[];
  running?: boolean;
}) {
  const data = useMemo(() => buildDiscoverTimeline(lines), [lines]);

  if (data.length < 2 && !running) return null;

  const chartData =
    data.length >= 2
      ? data
      : [
          { label: lines[0]?.verb ?? "start", value: 1 },
          { label: "scan", value: Math.max(1, lines.length) },
        ];

  return (
    <div className="bento-panel shrink-0" data-demo="discover-timeline">
      <div className="px-3 py-2 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          {running ? <span className="tape-live-dot" aria-hidden /> : null}
          <span className="font-mono text-[11px] uppercase text-ink-faint">Discover depth</span>
        </div>
        <span className="font-mono text-[11px] text-ink-faint">{lines.length} ops lines</span>
      </div>
      <div className="px-2 py-2 min-h-[140px] h-[140px]">
        <SimpleGraph
          data={chartData}
          height={128}
          lineColor="#191C19"
          dotColor="#3e6b4f"
          gridLines="horizontal"
          gridStyle="dashed"
          showDots
          curved={false}
          gradientFade={false}
          animationDuration={running ? 0.35 : 0.12}
          graphLineThickness={2}
          dotSize={5}
        />
      </div>
    </div>
  );
}
