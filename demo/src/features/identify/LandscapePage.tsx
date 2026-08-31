import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { ErrorState } from "@/components/ui/ErrorState";
import { StageShell } from "@/components/layout/StageShell";
import { StickyContinue } from "@/components/layout/StickyContinue";
import { COPY } from "@/lib/copy";
import { acceptCatalogSeed, useSessionSnapshot } from "@/lib/session-store";
import { useThreatMap } from "@/features/threat-map/useThreatMap";
import { TechniqueDetailDrawer } from "@/features/threat-map/TechniqueDetailDrawer";
import type { MergedTechnique } from "@/lib/api-types";
import { LandscapeGrid } from "./LandscapeGrid";
import { useIdentifyStream } from "./IdentifyLayout";

export function LandscapePage() {
  const session = useSessionSnapshot();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const highlightId = searchParams.get("highlight") ?? session.ui.highlightTechniqueId;
  const { byCategory, categoryLabels, isLoading, isError, refetch } = useThreatMap();
  const [selected, setSelected] = useState<MergedTechnique | null>(null);
  const { discover, running } = useIdentifyStream();
  const techniqueCount = Object.values(byCategory).flat().length;
  const canContinue = session.identify.approved.length >= 1;

  const onDiscover = () => {
    void discover("");
    navigate("/identify/discover");
  };

  return (
    <StageShell
      title={COPY.nav.identify}
      caption={COPY.identify.landscapeCaption}
      census={
        techniqueCount > 0 ? (
          <span className="font-mono text-[13px] text-ink-faint tabular-nums">{techniqueCount} techniques</span>
        ) : null
      }
      actions={
        <Button variant="primary" disabled={running} onClick={onDiscover} data-demo="discover">
          {COPY.identify.discover}
        </Button>
      }
      footer={
        canContinue ? (
          <StickyContinue to="/generate" label={COPY.identify.continue} demoId="continue-generate" />
        ) : (
          <footer className="glass-sheet sticky bottom-0 z-10 -mx-4 px-4 mt-auto shrink-0 h-12 flex items-center gap-3 rounded-t-sheet">
            <button
              type="button"
              className="text-[12px] text-ink-faint hover:text-ink underline-offset-2 hover:underline"
              onClick={() => acceptCatalogSeed()}
              data-demo="catalog-seed"
            >
              {COPY.identify.continueSeed}
            </button>
          </footer>
        )
      }
    >
      <div className="flex-1 min-h-0 flex flex-col">
        {isError ? <ErrorState message={COPY.identify.catalogFail} onRetry={() => void refetch()} /> : null}
        <LandscapeGrid
          byCategory={byCategory}
          categoryLabels={categoryLabels}
          onSelect={setSelected}
          highlightId={highlightId}
          loading={isLoading}
        />
      </div>
      <TechniqueDetailDrawer
        technique={selected}
        onClose={() => setSelected(null)}
        onDiscoverGap={(topic) => {
          void discover(topic);
          navigate("/identify/discover");
        }}
      />
    </StageShell>
  );
}
