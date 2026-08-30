import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/layout/Topbar";
import { Button } from "@/components/ui/Button";
import { ErrorState } from "@/components/ui/ErrorState";
import { COPY } from "@/lib/copy";
import { acceptCatalogSeed, useSessionSnapshot } from "@/lib/session-store";
import { useThreatMap } from "@/features/threat-map/useThreatMap";
import { TechniqueDetailDrawer } from "@/features/threat-map/TechniqueDetailDrawer";
import type { MergedTechnique } from "@/lib/api-types";
import { LandscapeGrid, LandscapeSkeleton } from "./LandscapeGrid";
import { ProposedAttackCards } from "./ProposedAttackCards";
import { SourceList, WorkLog } from "./WorkLog";
import { useDiscoverStream } from "./useDiscoverStream";
import { useHitlQueue } from "./useIdentify";

export function IdentifyPage() {
  const session = useSessionSnapshot();
  const [searchParams] = useSearchParams();
  const highlightId = searchParams.get("highlight") ?? session.ui.highlightTechniqueId;
  const { byCategory, categoryLabels, isLoading, isError, refetch } = useThreatMap();
  const [selected, setSelected] = useState<MergedTechnique | null>(null);
  const hitl = useHitlQueue(true);
  const {
    stage,
    lines,
    sources,
    running,
    error,
    discover,
    skip,
    follow,
    setFollow,
    newCount,
    clearNew,
  } = useDiscoverStream(() => void hitl.refetch());

  const techniqueCount = Object.values(byCategory).flat().length || 24;
  const canContinue = session.identify.approved.length >= 1;

  return (
    <div className="flex flex-col h-[calc(100vh-88px)] min-h-0">
      <PageHeader
        title={COPY.nav.identify}
        census={
          <span className="font-mono text-[48px] leading-none text-ink font-tabular" aria-label="24 techniques">
            {techniqueCount >= 24 ? 24 : techniqueCount}
          </span>
        }
        caption={COPY.identify.firstStillCaption}
        actions={
          <>
            {stage === "scanning" && session.ui.sourceChip === "recorded" ? (
              <Button variant="secondary" onClick={skip} data-demo="skip">
                {COPY.skip}
              </Button>
            ) : null}
            <Button
              variant="primary"
              disabled={running}
              aria-busy={running}
              onClick={() => void discover("")}
              data-demo="discover"
            >
              {COPY.identify.discover}
            </Button>
          </>
        }
      />

      {error ? (
        <p className="text-[13px] text-signal-block mb-2 border border-signal-block/30 bg-surface px-3 py-2 rounded">
          {error}
        </p>
      ) : null}

      {stage === "rest" ? (
        <div className="flex-1 min-h-0">
          {isLoading ? <LandscapeSkeleton /> : null}
          {isError ? (
            <ErrorState message={COPY.identify.catalogFail} onRetry={() => void refetch()} />
          ) : null}
          {!isLoading && !isError ? (
            <LandscapeGrid
              byCategory={byCategory}
              categoryLabels={categoryLabels}
              onSelect={setSelected}
              highlightId={highlightId}
            />
          ) : null}
        </div>
      ) : null}

      {stage === "scanning" ? (
        <div className="flex-1 flex flex-col gap-2 min-h-0">
          <LandscapeGrid
            byCategory={byCategory}
            categoryLabels={categoryLabels}
            onSelect={setSelected}
            compact
          />
          <div className="flex-1 grid grid-cols-[62%_38%] gap-3 min-h-0">
            <SourceList sources={sources} />
            <WorkLog
              lines={lines}
              follow={follow}
              onFollowChange={setFollow}
              newCount={newCount}
              onClearNew={clearNew}
            />
          </div>
        </div>
      ) : null}

      {stage === "review" ? (
        <div className="flex-1 grid grid-cols-[62%_38%] gap-3 min-h-0">
          <div className="overflow-y-auto min-h-0">
            <h2 className="font-mono text-[11px] uppercase text-ink-faint mb-2">{COPY.identify.review}</h2>
            <ProposedAttackCards items={hitl.data?.items ?? []} onApproved={() => void hitl.refetch()} />
          </div>
          <WorkLog
            lines={lines}
            follow={follow}
            onFollowChange={setFollow}
            newCount={newCount}
            onClearNew={clearNew}
          />
        </div>
      ) : null}

      <div className="mt-3 h-10 flex items-center gap-3 border-t border-border pt-2">
        {canContinue ? (
          <Link to="/generate">
            <Button variant="primary" data-demo="continue-generate">
              {COPY.identify.continue}
            </Button>
          </Link>
        ) : (
          <>
            <Button
              variant="secondary"
              onClick={() => acceptCatalogSeed()}
              data-demo="catalog-seed"
            >
              {COPY.identify.continueSeed}
            </Button>
            <span className="text-[12px] text-ink-faint">{COPY.identify.continueDisabled}</span>
          </>
        )}
      </div>

      <TechniqueDetailDrawer technique={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
