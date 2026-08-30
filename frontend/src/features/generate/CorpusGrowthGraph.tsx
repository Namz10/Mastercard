import { useMemo } from "react";
import clsx from "clsx";
import { SimpleGraph } from "@/components/ui/simple-graph";
import type { GenerateRunResponse } from "@/lib/api-types";
import { buildCorpusGrowthSeries } from "@/lib/graph-series";
import { formatInt } from "@/lib/format";
import { usePrefersReducedMotion } from "@/hooks/usePrefersReducedMotion";

export function CorpusGrowthGraph({
  run,
  running,
  seed,
}: {
  run: GenerateRunResponse | null;
  running: boolean;
  seed: number;
}) {
  const reducedMotion = usePrefersReducedMotion();
  const data = useMemo(() => {
    if (!run?.event_count) return [];
    return buildCorpusGrowthSeries(run.event_count, seed);
  }, [run?.event_count, seed]);

  return (
    <div
      className={clsx(
        "bento-panel workspace-card-lift flex flex-col min-h-[240px] shrink-0",
        running && !run && "corpus-building",
      )}
    >
      <div className="px-4 py-2 border-b border-border/60 flex items-baseline justify-between gap-2">
        <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint">Corpus growth</span>
        <span className="font-mono text-[13px] text-ink font-tabular">
          {run ? formatInt(run.event_count) : running ? "…" : "—"}
          {run ? <span className="text-ink-faint ml-1 text-[11px]">events</span> : null}
        </span>
      </div>
      <div className="px-3 py-2 flex-1 min-h-[200px]">
        {data.length > 0 ? (
          <SimpleGraph
            data={data}
            height={200}
            lineColor="#191C19"
            dotColor="#3e6b4f"
            gridLines="horizontal"
            gridStyle="dashed"
            showDots
            curved
            gradientFade
            animationDuration={reducedMotion ? 0 : 0.55}
            graphLineThickness={3}
            dotSize={6}
            dotHoverGlow
          />
        ) : (
          <div className="h-full min-h-[180px] flex items-center justify-center">
            <div className="text-center space-y-2">
              <div className="corpus-growth-placeholder mx-auto w-full max-w-[240px] h-[96px] rounded-xl border border-dashed border-border/70 bg-sage-100/20" />
              <p className="font-mono text-[10px] uppercase tracking-wide text-ink-faint">
                {running ? "Accumulating events…" : "Volume builds after simulate"}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
