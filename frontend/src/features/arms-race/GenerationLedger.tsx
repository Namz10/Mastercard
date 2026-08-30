import { useState, type ReactNode } from "react";
import clsx from "clsx";
import type { ArmsRaceViewModel } from "./arms-race-vm";
import { formatLedgerPct } from "./arms-race-vm";
import { formatPct } from "@/lib/format";

function Pill({
  children,
  tone = "gray",
}: {
  children: ReactNode;
  tone?: "red" | "green" | "gray" | "blue";
}) {
  const tones = {
    red: "bg-red-50 text-red-700 border-red-200",
    green: "bg-green-50 text-[#166534] border-green-200",
    gray: "bg-gray-50 text-ink-muted border-gray-200",
    blue: "bg-blue-50 text-[#2563EB] border-blue-200",
  };
  return (
    <span
      className={clsx(
        "inline-flex items-center px-2 py-0.5 rounded-full border font-mono text-[10px] uppercase tracking-wide",
        tones[tone],
      )}
    >
      {children}
    </span>
  );
}

function MetricChip({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex px-2 py-0.5 rounded bg-surface-sunken border border-border font-mono text-[10px] text-ink-muted">
      {children}
    </span>
  );
}

function SideCard({
  accent,
  label,
  title,
  body,
  pills,
  chips,
  muted,
}: {
  accent: string;
  label: string;
  title: string;
  body?: string;
  pills?: ReactNode;
  chips?: ReactNode;
  muted?: boolean;
}) {
  return (
    <div
      className={clsx(
        "relative bg-white border border-gray-200 rounded-lg p-4 border-l-[3px] transition-shadow",
        muted && "opacity-40 border-dashed",
      )}
      style={{ borderLeftColor: accent }}
    >
      {pills ? <div className="absolute top-3 right-3 flex gap-1">{pills}</div> : null}
      <p className="font-mono text-[10px] uppercase tracking-wide text-ink-faint mb-1">{label}</p>
      <h3 className="text-sm font-semibold text-ink mb-1 pr-16">{title}</h3>
      {body ? <p className="text-xs text-ink-muted leading-relaxed mb-2">{body}</p> : null}
      {chips ? <div className="flex flex-wrap gap-1.5 mt-2">{chips}</div> : null}
    </div>
  );
}

function TimelineDot({ gen, active, highlight }: { gen: string; active?: boolean; highlight?: boolean }) {
  return (
    <div
      className={clsx(
        "w-8 h-8 rounded-full border-2 flex items-center justify-center font-mono text-[10px] shrink-0 z-10 bg-white transition-colors",
        highlight ? "border-[#166534] text-[#166534] bg-green-50" : active ? "border-ink text-ink" : "border-gray-300 text-ink-faint",
      )}
    >
      {gen}
    </div>
  );
}

function GenerationRow({
  gen,
  red,
  outcome,
  blue,
  highlight,
  roadmap,
  expanded,
  onToggle,
  onClick,
  hovered,
  onHover,
}: {
  gen: string;
  red: ReactNode;
  outcome: ReactNode;
  blue: ReactNode;
  highlight?: boolean;
  roadmap?: boolean;
  expanded?: boolean;
  onToggle?: () => void;
  onClick?: () => void;
  hovered?: boolean;
  onHover?: (v: boolean) => void;
}) {
  return (
    <div
      className={clsx(
        "grid grid-cols-1 md:grid-cols-[auto_1fr] gap-3 md:gap-4 transition-all",
        highlight && "rounded-xl ring-1 ring-[#166534]/20 bg-green-50/30 p-2 -mx-2",
        hovered && !roadmap && "scale-[1.005]",
      )}
      onMouseEnter={() => onHover?.(true)}
      onMouseLeave={() => onHover?.(false)}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={(e) => {
        if (onClick && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          onClick();
        }
      }}
    >
      <div className="flex md:flex-col items-center md:items-center gap-2 md:pt-6">
        <TimelineDot gen={gen} active={!roadmap} highlight={highlight && hovered} />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-[5fr_2fr_5fr] gap-3 min-w-0">
        {red}
        <div className="flex flex-col items-center justify-center text-center px-2 py-3">{outcome}</div>
        <div className="relative">
          {blue}
          {onToggle ? (
            <button
              type="button"
              className="absolute top-2 right-2 text-ink-faint hover:text-ink text-xs"
              onClick={(e) => {
                e.stopPropagation();
                onToggle();
              }}
              aria-expanded={expanded}
              aria-label="Toggle generation details"
            >
              {expanded ? "▲" : "▼"}
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export function GenerationLedger({
  vm,
  onG1Click,
}: {
  vm: ArmsRaceViewModel["ledger"] &
    Pick<ArmsRaceViewModel, "apDelta" | "apVerdict" | "genuineFpOk" | "pass" | "gtestSeed">;
  onG1Click?: () => void;
}) {
  const [g1Expanded, setG1Expanded] = useState(false);
  const [hoveredGen, setHoveredGen] = useState<string | null>(null);

  const { family, nExtra, capPct, g0, g1 } = vm;

  return (
    <section className="bg-white border border-gray-200 rounded-xl p-5">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-6">
        <h2 className="text-sm font-semibold text-ink">Generation ledger</h2>
        <p className="font-mono text-xs text-ink-faint">
          miss_family={family} · n_extra={nExtra.toLocaleString()} · cap={capPct}%
        </p>
      </div>

      <div className="relative space-y-6 pl-0 md:pl-2">
        <div className="hidden md:block absolute left-[15px] top-8 bottom-8 w-px bg-gray-200" aria-hidden />

        <GenerationRow
          gen="G0"
          hovered={hoveredGen === "G0"}
          onHover={(v) => setHoveredGen(v ? "G0" : null)}
          red={
            <SideCard
              accent="#DC2626"
              label="RED · GENERATE"
              title={`${family} attack on frozen G-test`}
              body="Red injects catalog attack patterns onto the held-out G-test population."
              pills={<Pill tone="red">INJECTED</Pill>}
              chips={
                <span className="font-mono text-[10px] text-ink-faint">
                  seed={vm.gtestSeed} · family={family} · technique=T01
                </span>
              }
            />
          }
          outcome={
            <>
              <span className="inline-flex px-3 py-1 rounded-full bg-red-50 border border-red-200 font-mono text-xs text-red-700">
                {formatLedgerPct(g0.evasion)} evaded base model
              </span>
              <p className="text-[10px] text-ink-faint mt-1 font-mono">FN rate on {family} family</p>
            </>
          }
          blue={
            <SideCard
              accent="#2563EB"
              label="BLUE · BASE MODEL"
              title="Base model scored G-test"
              pills={<Pill tone="gray">BASE MODEL</Pill>}
              chips={
                <>
                  <MetricChip>Binary AP {formatLedgerPct(g0.binaryAp)}</MetricChip>
                  <MetricChip>Precision {formatLedgerPct(g0.precision)}</MetricChip>
                  <MetricChip>Recall {formatLedgerPct(g0.recall)}</MetricChip>
                  <MetricChip>genuine FPR {formatLedgerPct(g0.genuineFpr, 1)}</MetricChip>
                </>
              }
            />
          }
        />

        <GenerationRow
          gen="G1"
          highlight
          hovered={hoveredGen === "G1"}
          onHover={(v) => setHoveredGen(v ? "G1" : null)}
          onClick={onG1Click}
          expanded={g1Expanded}
          onToggle={() => setG1Expanded((v) => !v)}
          red={
            <SideCard
              accent="#DC2626"
              label="RED · GENERATE"
              title="Same family, independent G-test draw"
              body="Population rescored after blue retrain — red does not get train extras."
              pills={<Pill tone="red">RESCORE</Pill>}
              chips={
                <span className="font-mono text-[10px] text-ink-faint">
                  gtest_seed={vm.gtestSeed} · held-out events disjoint from train extras
                </span>
              }
            />
          }
          outcome={
            <>
              <span className="inline-flex px-3 py-1 rounded-full bg-green-50 border border-green-200 font-mono text-xs text-[#166534]">
                Feedback loop · +{formatPct(vm.apDelta, 2)} AP · evasion {formatLedgerPct(g0.evasion)} →{" "}
                {formatLedgerPct(g1.evasion)}
              </span>
              <p className="text-[10px] text-ink-faint mt-1 font-mono">
                verdict: {vm.apVerdict} · genuine FPR {vm.genuineFpOk ? "ok" : "warn"}
              </p>
            </>
          }
          blue={
            <>
              <SideCard
                accent="#166534"
                label="BLUE · POST FEEDBACK LOOP"
                title="Retrain on capped miss-family extras"
                body={`Extra ${family} rows appended to train copy only; G-test remains frozen new-seed protocol.`}
                pills={
                  <>
                    <Pill tone="green">RETRAIN PASS</Pill>
                    <Pill tone="gray">catalog_solved: false</Pill>
                  </>
                }
                chips={
                  <>
                    <MetricChip>Binary AP {formatLedgerPct(g1.binaryAp)}</MetricChip>
                    <MetricChip>Precision {formatLedgerPct(g1.precision)}</MetricChip>
                    <MetricChip>Recall {formatLedgerPct(g1.recall)}</MetricChip>
                    {g1.prAuc != null ? <MetricChip>PR-AUC {g1.prAuc.toFixed(2)}</MetricChip> : null}
                    {g1.apDelta != null ? (
                      <MetricChip>Δ AP +{formatPct(g1.apDelta, 2).replace("%", "pp")}</MetricChip>
                    ) : null}
                  </>
                }
              />
              {g1Expanded ? (
                <ul className="mt-2 ml-1 space-y-1 text-[11px] text-ink-muted font-mono list-disc list-inside">
                  <li>
                    {nExtra.toLocaleString()} extra rows · cap {capPct}% of train
                  </li>
                  <li>extra event IDs asserted disjoint from G-test</li>
                  <li>AP verdict: {vm.apVerdict} · genuine FPR within ε=0.02</li>
                  <li>solved is not auto-set — HITL only</li>
                </ul>
              ) : null}
            </>
          }
        />

        <GenerationRow
          gen="G2"
          roadmap
          hovered={hoveredGen === "G2"}
          onHover={(v) => setHoveredGen(v ? "G2" : null)}
          red={
            <SideCard
              accent="#DC2626"
              label="RED · CAT 4 (OFFLINE)"
              title="Masked field patch search"
              body="Oracle-guarded evasion probes — not exposed on public API."
              pills={<Pill tone="gray">ROADMAP</Pill>}
              muted
            />
          }
          outcome={
            <span className="inline-flex px-3 py-1 rounded-full bg-gray-50 border border-gray-200 font-mono text-xs text-ink-faint">
              Not demonstrated in v1
            </span>
          }
          blue={
            <SideCard
              accent="#2563EB"
              label="BLUE · LOOP A RESPONSE"
              title="Awaiting offline red-team round"
              pills={<Pill tone="gray">PLANNED</Pill>}
              muted
            />
          }
        />
      </div>
    </section>
  );
}
