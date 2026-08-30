import { useState } from "react";
import { PageHeader } from "@/components/layout/Topbar";
import { ErrorState } from "@/components/ui/ErrorState";
import { TechniqueDetailDrawer } from "./TechniqueDetailDrawer";
import { TechniqueGrid, TechniqueGridSkeleton } from "./TechniqueGrid";
import { useThreatMap } from "./useThreatMap";
import type { MergedTechnique } from "@/lib/api-types";

export function ThreatMapPage() {
  const { byCategory, categoryLabels, isLoading, isError, refetch } = useThreatMap();
  const [selected, setSelected] = useState<MergedTechnique | null>(null);

  return (
    <div>
      <PageHeader title="Threat Map" />
      {isLoading ? <TechniqueGridSkeleton /> : null}
      {isError ? (
        <ErrorState message="Could not load threat map — is the API running?" onRetry={() => void refetch()} />
      ) : null}
      {!isLoading && !isError
        ? [1, 2, 3, 4, 5].map((cat) => {
            const techniques = byCategory[cat] ?? [];
            if (techniques.length === 0) return null;
            return (
              <section key={cat} className="mb-8">
                <h2 className="font-mono text-xs uppercase text-ink-faint mb-3 tracking-wide">
                  {categoryLabels[cat]}
                </h2>
                <TechniqueGrid
                  techniques={techniques}
                  onSelect={setSelected}
                  selectedId={selected?.technique_id}
                />
              </section>
            );
          })
        : null}
      <TechniqueDetailDrawer technique={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
