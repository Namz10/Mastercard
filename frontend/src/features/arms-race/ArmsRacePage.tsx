import { PageHeader } from "@/components/layout/Topbar";
import { Button } from "@/components/ui/Button";
import { StatusChip } from "@/components/ui/StatusChip";
import { GTestChart } from "./GTestChart";
import { useArmsRace } from "./useArmsRace";
import { formatPct } from "@/lib/format";

export function ArmsRacePage() {
  const { loopM, staticScore, runId } = useArmsRace();
  const delta = loopM.data?.comparison?.ap_delta;

  return (
    <div>
      <PageHeader
        title="Arms Race"
        actions={
          <>
            {delta != null ? (
              <StatusChip status={delta >= 0 ? "pass" : "fail"} />
            ) : null}
            {delta != null ? (
              <span className="text-xs font-mono text-signal-safe">
                {delta >= 0 ? "+" : ""}
                {formatPct(delta, 2)} AP
              </span>
            ) : null}
            <Button
              variant="primary"
              disabled={!runId || loopM.isPending}
              onClick={() => loopM.mutate()}
              data-demo="run-loop-m"
            >
              {loopM.isPending ? "Running Loop M…" : "Run Loop M"}
            </Button>
          </>
        }
      />
      {!runId ? (
        <p className="text-sm text-ink-muted mb-4">Complete the generate → defend pipeline first.</p>
      ) : null}
      {loopM.isError ? (
        <p className="text-sm text-signal-block mb-4">Loop M failed — fit and score the run on Decisioning first.</p>
      ) : null}
      <GTestChart staticScore={staticScore} loopM={loopM.data ?? null} />
    </div>
  );
}
