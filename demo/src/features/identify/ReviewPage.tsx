import { Button } from "@/components/ui/Button";
import { StageShell } from "@/components/layout/StageShell";
import { StickyContinue } from "@/components/layout/StickyContinue";
import { CatalogThread } from "@/components/ui/CatalogThread";
import { COPY } from "@/lib/copy";
import { pendingHitlItems } from "@/lib/hitl-dedupe";
import { acceptCatalogSeed, useSessionSnapshot } from "@/lib/session-store";
import { ProposedAttackCards } from "./ProposedAttackCards";
import { useIdentifyStream } from "./IdentifyLayout";

export function ReviewPage() {
  const session = useSessionSnapshot();
  const { lines, hitl } = useIdentifyStream();
  const pending = pendingHitlItems(hitl.data?.items ?? []);
  const canContinue = session.identify.approved.length >= 1;
  const fetching = hitl.isFetching && !hitl.data;

  return (
    <StageShell
      title={COPY.nav.identify}
      caption={COPY.identify.reviewCaption}
      footer={
        canContinue ? (
          <StickyContinue to="/generate" label={COPY.identify.continue} demoId="continue-generate" />
        ) : (
          <footer className="glass-sheet sticky bottom-0 z-10 -mx-4 px-4 mt-auto shrink-0 h-12 flex items-center gap-3 rounded-t-sheet">
            <button
              type="button"
              className="text-[12px] text-ink-faint hover:text-ink underline-offset-2 hover:underline"
              onClick={() => acceptCatalogSeed()}
            >
              {COPY.identify.continueSeed}
            </button>
          </footer>
        )
      }
    >
      <div className="flex-1 grid grid-cols-[62%_38%] gap-3 min-h-0">
        <div className="overflow-y-auto min-h-0">
          {fetching ? (
            <p className="text-[13px] text-ink-muted font-mono">Loading proposals…</p>
          ) : pending.length === 0 && (hitl.data?.items?.length ?? 0) === 0 ? (
            <div className="bento-panel p-8 text-center">
              <p className="text-[16px] font-medium text-ink mb-4">{COPY.identify.emptyProposed}</p>
              <Button variant="secondary" onClick={() => acceptCatalogSeed()} data-demo="catalog-seed">
                {COPY.identify.continueSeed}
              </Button>
            </div>
          ) : (
            <ProposedAttackCards items={hitl.data?.items ?? []} onApproved={() => void hitl.refetch()} />
          )}
        </div>
        <CatalogThread lines={lines} running={false} emptyLabel={COPY.identify.review} />
      </div>
    </StageShell>
  );
}
