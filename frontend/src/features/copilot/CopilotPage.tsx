import { useEffect } from "react";
import { ErrorState } from "@/components/ui/ErrorState";
import { Spinner } from "@/components/ui/Spinner";
import { ClosedLoopDiagram } from "./ClosedLoopDiagram";
import { CoverageHeatmap } from "./CoverageHeatmap";
import { ExecutiveBrief } from "./ExecutiveBrief";
import { HeroStrip } from "./HeroStrip";
import { LabPulse } from "./LabPulse";
import { LoopMaturity } from "./LoopMaturity";
import { PillarCards } from "./PillarCards";
import { ReportCards } from "./ReportCards";
import { useCommandCenter } from "./useCommandCenter";

export function CopilotPage() {
  const { snapshot, isLoading, isError, error, refetch, brief } = useCommandCenter();

  useEffect(() => {
    document.title = "Command Center · AegisLoop";
    return () => {
      document.title = "AegisLoop";
    };
  }, []);

  if (isLoading && !snapshot) {
    return (
      <div className="py-16">
        <Spinner label="Loading command center…" />
      </div>
    );
  }

  if (isError && !snapshot) {
    return (
      <ErrorState
        message={(error as Error)?.message ?? "Failed to load command center snapshot"}
        onRetry={() => void refetch()}
      />
    );
  }

  if (!snapshot) {
    return <ErrorState message="No snapshot available" onRetry={() => void refetch()} />;
  }

  return (
    <div className="max-w-6xl mx-auto pb-12">
      {/* Zone 0 */}
      <HeroStrip
        kpis={snapshot.kpis}
        system={snapshot.system}
        generatedAt={snapshot.generated_at}
      />

      {/* Zone 1 */}
      <ClosedLoopDiagram phaseStatus={snapshot.phase_status} />

      {/* Zone 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-8">
        <div className="lg:col-span-8">
          <CoverageHeatmap cells={snapshot.coverage?.cells ?? []} />
        </div>
        <div className="lg:col-span-4">
          <PillarCards snapshot={snapshot} />
        </div>
      </div>

      {/* Zone 3 */}
      <LabPulse events={snapshot.lab_events ?? []} />

      {/* Zone 4 */}
      <ReportCards snapshot={snapshot} />

      {/* Zone 5 */}
      <LoopMaturity loops={snapshot.loops ?? {}} />

      {/* Zone 6 */}
      <ExecutiveBrief brief={brief} />

      <div className="mt-2 flex flex-wrap gap-2 font-mono text-[10px] text-ink-faint">
        <span className="rounded border border-border px-2 py-0.5">synthetic_only: true</span>
        <span className="rounded border border-border px-2 py-0.5">catalog_solved: false</span>
        <span className="rounded border border-border px-2 py-0.5">Cat 4 offline · no public attack API</span>
        <span className="rounded border border-border px-2 py-0.5">LLM not the detector</span>
      </div>
    </div>
  );
}
