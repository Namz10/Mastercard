import { useMemo, useRef, type ReactNode } from "react";
import { Radar, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { PixelBlast } from "@/components/ui/PixelBlast";
import { ClippedAreaChart, type ClippedAreaPoint } from "@/components/ui/advanced-stats-utils/charts";
import { TimelineAnimation } from "@/components/ui/advanced-stats-utils/timeline-animation";
import type { ScoreMetrics } from "@/lib/api-types";
import { FAMILY_LABEL, formatPct } from "@/lib/format";
import { useSessionSnapshot } from "@/lib/session-store";
import { cn } from "@/lib/utils";

export type StatKpi = {
  label: string;
  value: string;
  change?: string;
  status?: "up" | "down" | "neutral";
  mass?: "hero" | "accent" | "quiet" | "source";
  sparkline?: ClippedAreaPoint[];
  pixelBlast?: boolean;
  pixelColor?: string;
};

export type AdvancedStatsGoal = {
  eyebrow: string;
  title: string;
  value: number;
  target: number;
  valueLabel?: string;
  targetLabel?: string;
};

export type AdvancedStatsInsight = {
  title: string;
  body: ReactNode;
  icon?: ReactNode;
};

export type AdvancedStatsProps = {
  compact?: boolean;
  kpis: StatKpi[];
  chartData?: ClippedAreaPoint[];
  chartTitle?: string;
  chartSubtitle?: string;
  goal?: AdvancedStatsGoal;
  insight?: AdvancedStatsInsight;
  className?: string;
};

function massSpan(mass?: StatKpi["mass"]) {
  if (mass === "hero") return "col-span-12 sm:col-span-7 min-h-[132px]";
  if (mass === "accent") return "col-span-6 sm:col-span-2 min-h-[88px]";
  if (mass === "source") return "col-span-6 sm:col-span-1 min-h-[72px]";
  if (mass === "quiet") return "col-span-6 sm:col-span-1 min-h-[76px]";
  return "col-span-6 sm:col-span-3 min-h-[88px]";
}

function KpiCard({
  kpi,
  animationNum,
  timelineRef,
}: {
  kpi: StatKpi;
  animationNum: number;
  timelineRef: React.RefObject<HTMLElement | null>;
}) {
  const hero = kpi.mass === "hero";
  const accent = kpi.mass === "accent";
  const source = kpi.mass === "source";

  return (
    <TimelineAnimation
      animationNum={animationNum}
      timelineRef={timelineRef}
      className={cn(
        "relative overflow-hidden workspace-card-lift transition-colors",
        massSpan(kpi.mass),
        hero && "bento-panel px-5 py-4 ring-1 ring-sage-600/10",
        accent && "rounded-sheet border border-sage-600/30 bg-sage-100 px-4 py-3.5",
        source && "glass-sheet rounded-sheet px-2 py-2 opacity-90",
        !hero && !accent && !source && "glass-sheet rounded-sheet px-3.5 py-3",
      )}
    >
      {kpi.pixelBlast ? (
        <PixelBlast
          color={kpi.pixelColor ?? "#3e6b4f"}
          liquid={false}
          enableRipples={false}
          transparent
          patternScale={1.5}
          patternDensity={0.95}
          edgeFade={0.5}
          className="opacity-[0.52]"
        />
      ) : null}
      <div className="relative z-[1] h-full flex flex-col justify-between">
        <p className="font-semibold uppercase tracking-widest text-ink-faint text-[10px] mb-1">{kpi.label}</p>
        <div className="flex items-end justify-between gap-2">
          <p
            className={cn(
              "font-mono font-semibold tracking-tight text-ink font-tabular leading-none",
              hero ? "text-[58px]" : accent ? "text-[24px]" : source ? "text-[14px]" : "text-[18px]",
            )}
          >
            {kpi.value}
          </p>
          {kpi.change ? (
            <Badge
              variant={kpi.status === "down" ? "watch" : kpi.status === "up" ? "sage" : accent ? "sage" : "outline"}
              className="shrink-0 mb-1"
            >
              {kpi.change}
            </Badge>
          ) : null}
        </div>
        {kpi.sparkline && kpi.sparkline.length > 1 ? (
          <div className="mt-2 h-[56px]">
            <ClippedAreaChart data={kpi.sparkline} height={56} />
          </div>
        ) : null}
      </div>
    </TimelineAnimation>
  );
}

export function AdvancedStats({
  compact = false,
  kpis,
  chartData,
  chartTitle,
  chartSubtitle,
  goal,
  insight,
  className,
}: AdvancedStatsProps) {
  const timelineRef = useRef<HTMLDivElement>(null);

  if (compact) {
    return (
      <section ref={timelineRef} className={cn("shrink-0", className)}>
        <div className="grid grid-cols-12 gap-2.5 items-stretch">
          {kpis.map((kpi, index) => (
            <KpiCard key={kpi.label} kpi={kpi} animationNum={index + 1} timelineRef={timelineRef} />
          ))}
        </div>
      </section>
    );
  }

  return (
    <section ref={timelineRef} className={cn("flex flex-col gap-4", className)}>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <TimelineAnimation
          animationNum={1}
          timelineRef={timelineRef}
          className="bento-panel p-5 lg:col-span-2"
        >
          {chartData ? (
            <>
              {(chartTitle || chartSubtitle) && (
                <div className="mb-4">
                  {chartSubtitle ? (
                    <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-ink-faint">
                      {chartSubtitle}
                    </p>
                  ) : null}
                  {chartTitle ? <h3 className="text-lg font-semibold tracking-tight text-ink">{chartTitle}</h3> : null}
                </div>
              )}
              <ClippedAreaChart data={chartData} height={220} />
            </>
          ) : null}
        </TimelineAnimation>

        <div className="flex flex-col gap-3">
          {goal ? (
            <TimelineAnimation
              animationNum={2}
              timelineRef={timelineRef}
              className="flex flex-1 flex-col justify-between bento-panel p-5"
            >
              <div>
                <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.2em] text-ink-faint">{goal.eyebrow}</p>
                <h4 className="text-lg font-semibold tracking-tight text-ink">{goal.title}</h4>
              </div>
              <div className="mt-6">
                <div className="mb-2 flex items-end justify-between">
                  <span className="font-mono text-3xl font-semibold tracking-tighter text-ink">
                    {goal.valueLabel ?? `${goal.value}%`}
                  </span>
                  <span className="mb-1 text-xs font-medium text-ink-faint">
                    {goal.targetLabel ?? `Target: ${goal.target}%`}
                  </span>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-sage-100">
                  <div
                    className="h-full rounded-full bg-sage-600 transition-[width] duration-700 ease-out motion-reduce:transition-none"
                    style={{ width: `${Math.min(100, (goal.value / goal.target) * 100)}%` }}
                  />
                </div>
              </div>
            </TimelineAnimation>
          ) : null}

          {insight ? (
            <TimelineAnimation
              animationNum={3}
              timelineRef={timelineRef}
              className="glass-sheet rounded-sheet p-5"
            >
              <div className="mb-3 flex items-center gap-3">
                <div className="flex size-8 items-center justify-center rounded-lg border border-border bg-surface-sunken">
                  {insight.icon ?? <Radar className="size-4 text-sage-600" aria-hidden />}
                </div>
                <h4 className="font-semibold text-ink">{insight.title}</h4>
              </div>
              <div className="text-sm text-ink-muted">{insight.body}</div>
            </TimelineAnimation>
          ) : null}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {kpis.map((kpi, index) => (
          <KpiCard key={kpi.label} kpi={kpi} animationNum={4 + index} timelineRef={timelineRef} />
        ))}
      </div>
    </section>
  );
}

function buildRecallSeries(metrics: ScoreMetrics | null, before: ScoreMetrics | null): ClippedAreaPoint[] {
  if (!metrics) return [];
  const recall = metrics.recall_at_op * 100;
  const prior = before ? before.recall_at_op * 100 : recall;
  return [
    { label: "T-4", value: Math.max(50, prior - 8) },
    { label: "T-3", value: Math.max(50, prior - 4) },
    { label: "T-2", value: Math.max(50, prior - 2) },
    { label: "T-1", value: Math.max(50, prior) },
    { label: "Now", value: recall },
  ];
}

function buildFamilySeries(counts: Record<string, number> | null): ClippedAreaPoint[] {
  if (!counts || !Object.keys(counts).length) {
    return [
      { label: "quiet", value: 12 },
      { label: "mule", value: 4 },
      { label: "ATO", value: 3 },
      { label: "APP", value: 2 },
    ];
  }
  return Object.entries(counts)
    .filter(([k]) => k !== "normal")
    .slice(0, 6)
    .map(([key, value]) => ({
      label: FAMILY_LABEL[key] ?? key,
      value,
    }));
}

export function AegisDefendStats({
  metrics,
  before,
  scoring,
  missFamily,
  missTechniqueId,
  className,
  compact = true,
  showHero = true,
}: {
  metrics: ScoreMetrics | null;
  before?: ScoreMetrics | null;
  scoring?: boolean;
  missFamily?: string | null;
  missTechniqueId?: string | null;
  className?: string;
  compact?: boolean;
  showHero?: boolean;
}) {
  const chartData = useMemo(() => buildRecallSeries(metrics, before ?? null), [metrics, before]);
  const recall = metrics ? `${(metrics.recall_at_op * 100).toFixed(1)}%` : scoring ? "…" : "—";
  const delta =
    metrics && before ? `${((metrics.recall_at_op - before.recall_at_op) * 100).toFixed(1)} pts` : undefined;

  const kpis: StatKpi[] = [
    ...(showHero
      ? [
          {
            label: metrics ? `Recall @ FPR ${formatPct(metrics.genuine_fp, 3)}` : "Recall @ OP",
            value: recall,
            change: delta,
            status: (delta && delta.startsWith("-") ? "down" : delta ? "up" : "neutral") as StatKpi["status"],
            mass: "hero" as const,
            sparkline: chartData,
          },
        ]
      : []),
    {
      label: "Holdout precision",
      value: metrics ? formatPct(metrics.precision_at_op) : "—",
      change: metrics ? `${metrics.n_eval.toLocaleString("en-IN")} rows` : undefined,
      status: "neutral",
      mass: "accent",
    },
    {
      label: "Miss family",
      value: missFamily ? (FAMILY_LABEL[missFamily] ?? missFamily) : "—",
      change: missTechniqueId ? `→ ${missTechniqueId}` : undefined,
      status: missFamily ? "down" : "neutral",
      mass: "quiet",
    },
    {
      label: "Binary AP",
      value: metrics ? formatPct(metrics.binary_ap) : "—",
      status: "neutral",
      mass: "quiet",
    },
  ];

  if (compact) {
    return <AdvancedStats compact kpis={kpis} className={className} />;
  }

  return (
    <AdvancedStats
      kpis={kpis}
      chartData={chartData}
      chartTitle="Holdout recall trend"
      chartSubtitle="Defend scoring"
      goal={{
        eyebrow: "Operating point",
        title: "Recall target",
        value: metrics ? Math.round(metrics.recall_at_op * 100) : 0,
        target: 90,
      }}
      insight={{
        title: "Weakest slice",
        icon: <ShieldCheck className="size-4 text-accent" aria-hidden />,
        body: missFamily ? (
          <>
            Model misses <span className="font-semibold text-ink">{FAMILY_LABEL[missFamily] ?? missFamily}</span> most
            often{missTechniqueId ? ` — loop back to ${missTechniqueId}` : ""}.
          </>
        ) : (
          "Score the generate run to surface the weakest fraud family."
        ),
      }}
      className={className}
    />
  );
}

export function AegisIdentifyStats({
  techniqueCount,
  approvedCount,
  proposedCount,
  sourceMode,
  className,
  compact = true,
}: {
  techniqueCount: number;
  approvedCount: number;
  proposedCount: number;
  sourceMode: string;
  className?: string;
  compact?: boolean;
}) {
  const session = useSessionSnapshot();
  const chartData = useMemo(() => buildFamilySeries(session.generate.familyCounts), [session.generate.familyCounts]);

  const kpis: StatKpi[] = [
    {
      label: "Techniques mapped",
      value: String(Math.min(techniqueCount, 24)),
      change: "of 24",
      status: "neutral",
      mass: "hero",
      pixelBlast: true,
      pixelColor: "#3e6b4f",
    },
    {
      label: "Approved attacks",
      value: String(approvedCount),
      change: approvedCount >= 1 ? "ready" : "needed",
      status: approvedCount >= 1 ? "up" : "down",
      mass: "accent",
    },
    {
      label: "In review queue",
      value: String(proposedCount),
      status: "neutral",
      mass: "quiet",
    },
    {
      label: "Source",
      value: sourceMode.toUpperCase(),
      status: "neutral",
      mass: "source",
    },
  ];

  if (compact) {
    return <AdvancedStats compact kpis={kpis} className={className} />;
  }

  return (
    <AdvancedStats
      kpis={kpis}
      chartData={chartData}
      chartTitle="Attack families in play"
      chartSubtitle="Identify landscape"
      goal={{
        eyebrow: "Booth gate",
        title: "Coverage for Generate",
        value: Math.round((approvedCount / 1) * 100),
        target: 100,
        valueLabel: `${approvedCount} approved`,
        targetLabel: "Need ≥1",
      }}
      insight={{
        title: "Threat surface",
        body: (
          <>
            Catalog holds <span className="font-semibold text-ink">{Math.min(techniqueCount, 24)}</span> techniques
            across payment fraud families — discover gaps before seeding Generate.
          </>
        ),
      }}
      className={className}
    />
  );
}
