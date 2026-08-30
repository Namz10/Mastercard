import { Link, useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/layout/Topbar";
import { Button } from "@/components/ui/Button";
import { AegisIdentifyStats } from "@/components/ui/advanced-stats";
import { Spinner } from "@/components/ui/Spinner";
import { COPY } from "@/lib/copy";
import { pendingHitlItems } from "@/lib/hitl-dedupe";
import { acceptCatalogSeed, useSessionSnapshot } from "@/lib/session-store";
import { useThreatMap } from "@/features/threat-map/useThreatMap";
import { TechniqueDetailDrawer } from "@/features/threat-map/TechniqueDetailDrawer";
import type { MergedTechnique } from "@/lib/api-types";
import { useState } from "react";
import { LandscapeGrid } from "./LandscapeGrid";
import { ProposedAttackCards } from "./ProposedAttackCards";
import { DiscoverTimelineGraph } from "./DiscoverTimelineGraph";
import { ErrorState } from "@/components/ui/ErrorState";
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
  const recordedPlayback = session.ui.sourceChip !== "live";

  return (
    <div className="identify-atmosphere flex flex-col h-full min-h-0 relative -mx-4 -my-3 px-4 py-3">
      <PageHeader
        title={COPY.nav.identify}
        actions={
          <Button
            variant="primary"
            disabled={running}
            aria-busy={running}
            onClick={() => void discover("")}
            data-demo="discover"
          >
            {COPY.identify.discover}
          </Button>
        }
      />

      {error ? (
        <p className="text-[13px] text-signal-block mb-2 border border-signal-block/30 bg-surface px-3 py-2 rounded">
          {error}
        </p>
      ) : null}

      {stage === "rest" ? (
        <div className="flex-1 min-h-0 flex flex-col gap-2">
          <AegisIdentifyStats
            techniqueCount={techniqueCount}
            approvedCount={session.identify.approved.length}
            proposedCount={pendingHitlItems(hitl.data?.items ?? []).length || session.identify.proposedIds.length}
            sourceMode={session.ui.sourceChip}
          />
          {isLoading ? (
            <div className="flex-1 bento-panel flex items-center justify-center">
              <Spinner label="Loading catalog…" />
            </div>
          ) : null}
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
        <div className="flex-1 flex flex-col gap-2 min-h-0" data-demo="discover-scanning">
          <div className="bento-panel shrink-0 flex items-center gap-3 px-3 py-2.5">
            <Spinner label="" />
            <div className="min-w-0 flex-1">
              <p className="font-mono text-[11px] uppercase text-ink-faint">{COPY.identify.scanning}</p>
              <p className="text-[13px] text-ink truncate">
                {lines[lines.length - 1]?.body ?? "Starting collectors…"}
              </p>
            </div>
            <span className="tape-live-dot shrink-0" aria-hidden />
          </div>
          <DiscoverTimelineGraph lines={lines} running={running} />
          <LandscapeGrid
            byCategory={byCategory}
            categoryLabels={categoryLabels}
            onSelect={setSelected}
            compact
          />
          <div className="flex-1 grid grid-cols-[62%_38%] gap-3 min-h-0">
            <SourceList sources={sources} running={running} />
            <WorkLog
              lines={lines}
              follow={follow}
              onFollowChange={setFollow}
              newCount={newCount}
              onClearNew={clearNew}
              running={running}
            />
          </div>
          {recordedPlayback ? (
            <div className="flex justify-end">
              <Button variant="secondary" onClick={skip} data-demo="skip">
                {COPY.skip}
              </Button>
            </div>
          ) : null}
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

      <div className="glass-sheet sticky bottom-0 z-10 -mx-4 px-4 mt-auto shrink-0 h-12 flex items-center gap-3 rounded-t-sheet">
        {canContinue ? (
          <Link to="/generate">
            <Button variant="primary" data-demo="continue-generate">
              {COPY.identify.continue}
            </Button>
          </Link>
        ) : (
          <>
            <Button variant="secondary" onClick={() => acceptCatalogSeed()} data-demo="catalog-seed">
              {COPY.identify.continueSeed}
            </Button>
            <span className="text-[12px] text-ink-faint">{COPY.identify.continueDisabled}</span>
          </>
        )}
      </div>

      <TechniqueDetailDrawer
        technique={selected}
        onClose={() => setSelected(null)}
        onDiscoverGap={(topic) => void discover(topic)}
      />
    </div>
  );
}
