import { useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { CatalogSourceDeck } from "@/components/ui/CatalogSourceDeck";
import { CatalogThread } from "@/components/ui/CatalogThread";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { StageShell } from "@/components/layout/StageShell";
import { COPY } from "@/lib/copy";
import { useSessionSnapshot } from "@/lib/session-store";
import { useIdentifyStream } from "./IdentifyLayout";

export function DiscoverPage() {
  const session = useSessionSnapshot();
  const navigate = useNavigate();
  const sentToReview = useRef(false);
  const { lines, sources, running, error, discover, skip, hitl } = useIdentifyStream();
  const recordedPlayback = session.ui.sourceChip !== "live";
  const hasThread = running || lines.length > 0;
  const completed = Boolean(session.identify.runId) && !running;

  useEffect(() => {
    if (running) sentToReview.current = false;
    if (!running && lines.length > 0 && session.identify.runId && !sentToReview.current) {
      sentToReview.current = true;
      navigate("/identify/review", { replace: true });
    }
  }, [running, lines.length, session.identify.runId, navigate]);

  const sourceCount = sources.length;
  const lastLine = lines[lines.length - 1];

  return (
    <StageShell title={COPY.nav.identify} caption={COPY.identify.discoverCaption}>
      {error ? (
        <ErrorBanner message={error} onRetry={() => void discover("")} hint="⌘K for recorded pack" />
      ) : null}

      {!hasThread && !completed ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-4 px-6">
          <p className="text-[14px] text-ink-muted text-center max-w-md">
            Start catalog research from Landscape, or load the recorded pack (⌘K).
          </p>
          <Button variant="primary" onClick={() => navigate("/identify")} data-demo="discover-back-landscape">
            {COPY.identify.discover}
          </Button>
        </div>
      ) : (
        <>
          <div
            className="shrink-0 h-12 flex items-center px-3 bento-panel mb-2 catalog-scan-banner"
            data-demo="discover-scanning"
          >
            <p className="text-[13px] text-ink">
              {running
                ? `${COPY.identify.scanning} — ${sourceCount} catalog sources`
                : completed
                  ? "Catalog research complete"
                  : lastLine?.body ?? COPY.identify.scanning}
            </p>
            {running ? <span className="tape-live-dot shrink-0 ml-auto" aria-hidden /> : null}
          </div>
          <div className="flex-1 grid grid-cols-[62%_38%] gap-3 min-h-0">
            <CatalogSourceDeck sources={sources} running={running} />
            <CatalogThread lines={lines} running={running} emptyLabel={COPY.identify.scanning} />
          </div>
          {completed && !running ? (
            <div className="flex justify-end mt-2 gap-2">
              <Link
                to="/identify/review"
                className="text-[13px] text-ink-muted hover:text-ink underline-offset-2 hover:underline"
              >
                Open review queue
              </Link>
            </div>
          ) : null}
        </>
      )}

      {recordedPlayback && hasThread ? (
        <div className="flex justify-end mt-2">
          <Button
            variant="secondary"
            onClick={() => {
              skip();
              void hitl.refetch();
              navigate("/identify/review");
            }}
            data-demo="skip"
          >
            {COPY.skip}
          </Button>
        </div>
      ) : null}
    </StageShell>
  );
}
