import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronDown } from "lucide-react";
import { PageHeader } from "@/components/layout/Topbar";
import { Button } from "@/components/ui/Button";
import { StatusChip } from "@/components/ui/StatusChip";
import { COPY } from "@/lib/copy";
import { formatInt } from "@/lib/format";
import { useSessionSnapshot } from "@/lib/session-store";
import type { GenerateRunResponse } from "@/lib/api-types";
import { useGenerate } from "./useGenerate";
import { LedgerTape } from "./LedgerTape";
import { LayeredMuleGraph } from "./LayeredMuleGraph";
import { SeedStamp } from "./SeedStamp";
import { CorpusGrowthGraph } from "./CorpusGrowthGraph";

export function GeneratePage() {
  const session = useSessionSnapshot();
  const { simulate, canary } = useGenerate();
  const running = simulate.isPending || canary.isPending;
  const fidelityKnown = session.generate.fidelityPass != null;
  const seed = session.generate.seed ?? 42;
  const [moreOpen, setMoreOpen] = useState(false);
  const moreRef = useRef<HTMLDivElement>(null);
  const sessionRun: GenerateRunResponse | null = session.generate.runId
    ? {
        run_id: session.generate.runId,
        mode: session.generate.scale,
        parquet_path: "",
        sidecar_path: "",
        fidelity: {
          pass: session.generate.fidelityPass ?? false,
          mule_fan_in_median: session.generate.muleFanIn ?? undefined,
        },
        counts_by_label_family: session.generate.familyCounts ?? {},
        event_count: session.generate.eventCount ?? 0,
        world_seed: session.generate.seed ?? 42,
      }
    : null;
  const run = simulate.data ?? canary.data ?? sessionRun;
  const autoRan = useRef(false);
  const showFloatingSimulate = !run && !running;

  useEffect(() => {
    if (autoRan.current || run || running) return;
    if (session.identify.approved.length < 1) return;
    autoRan.current = true;
    simulate.mutate("demo");
  }, [run, running, session.identify.approved.length, simulate]);

  useEffect(() => {
    if (!moreOpen) return;
    const close = (e: MouseEvent) => {
      if (moreRef.current && !moreRef.current.contains(e.target as Node)) setMoreOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [moreOpen]);

  const onSimulate = () => simulate.mutate("demo");

  return (
    <div className="generate-atmosphere flex flex-col h-full min-h-0 relative -mx-4 -my-3 px-4 py-3">
      <PageHeader
        title={COPY.nav.generate}
        caption="Synthetic payment traffic · reproducible seed"
        actions={
          <div className="flex items-center gap-2">
            <div className="relative hidden sm:block" ref={moreRef}>
              <Button
                variant="ghost"
                disabled={running}
                className="gap-1.5 pr-3"
                onClick={() => setMoreOpen((v) => !v)}
                aria-expanded={moreOpen}
              >
                Modes
                <ChevronDown className="w-3.5 h-3.5 opacity-60" />
              </Button>
              {moreOpen ? (
                <div className="absolute right-0 top-[calc(100%+6px)] z-20 glass-sheet rounded-drawer p-1 min-w-[240px] shadow-float">
                  <button
                    type="button"
                    className="w-full text-left px-3 py-2.5 text-[13px] rounded-md hover:bg-accent-muted transition-colors"
                    onClick={() => {
                      setMoreOpen(false);
                      simulate.mutate("full");
                    }}
                  >
                    {COPY.generate.fullPopulation}
                  </button>
                  <button
                    type="button"
                    className="w-full text-left px-3 py-2.5 text-[13px] rounded-md hover:bg-accent-muted transition-colors"
                    onClick={() => {
                      setMoreOpen(false);
                      canary.mutate();
                    }}
                  >
                    {COPY.generate.canary}
                  </button>
                </div>
              ) : null}
            </div>
            <Button variant="primary" disabled={running} onClick={onSimulate} data-demo="simulate">
              {COPY.generate.primary}
            </Button>
          </div>
        }
      />

      {simulate.error || canary.error ? (
        <p className="text-[13px] text-signal-block mb-2 border border-signal-block/30 bg-surface px-3 py-2 rounded-sheet">
          Approved recipes missing — using catalog seed, or retry.
        </p>
      ) : null}

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-[minmax(0,60fr)_minmax(0,40fr)] gap-3 min-h-0">
        <LedgerTape
          run={run}
          running={running}
          seed={seed}
          onSimulate={onSimulate}
          simulateDisabled={running}
        />
        <div className="flex flex-col min-h-0 gap-2.5">
          <SeedStamp seed={seed} />
          <CorpusGrowthGraph run={run} running={running} seed={seed} />
          <LayeredMuleGraph run={run} running={running} />
        </div>
      </div>

      {showFloatingSimulate ? (
        <div className="pointer-events-none fixed bottom-20 left-1/2 z-20 -translate-x-1/2 lg:absolute lg:bottom-16 lg:left-[30%]">
          <Button
            variant="primary"
            disabled={running}
            onClick={onSimulate}
            className="pointer-events-auto h-11 px-6 shadow-[0_8px_28px_rgba(62,107,79,0.32)]"
            data-demo="simulate-float"
          >
            {COPY.generate.primary}
          </Button>
        </div>
      ) : null}

      <footer className="generate-footer glass-sheet sticky bottom-0 z-10 -mx-1 px-4 mt-2.5 shrink-0 h-12 flex items-center gap-3 rounded-sheet">
        <div className="flex items-center gap-2 min-w-0">
          {fidelityKnown ? (
            session.generate.fidelityPass ? (
              <StatusChip status="pass" />
            ) : (
              <StatusChip status="fail" />
            )
          ) : running ? (
            <span className="font-mono text-[10px] uppercase tracking-wide text-ink-faint">
              {COPY.generate.fidelityChecking}
            </span>
          ) : (
            <span className="font-mono text-[10px] uppercase tracking-wide text-ink-faint truncate">
              {COPY.generate.continueDisabled}
            </span>
          )}
        </div>
        {run ? (
          <span className="font-mono text-[11px] text-ink-faint tabular-nums">
            {formatInt(run.event_count)} events
          </span>
        ) : null}
        <div className="ml-auto flex items-center gap-2">
          {fidelityKnown ? (
            <Link to="/defend">
              <Button variant="primary" className="h-9 px-5" data-demo="continue-defend">
                {COPY.generate.continue}
              </Button>
            </Link>
          ) : null}
        </div>
      </footer>
    </div>
  );
}
