import { AdvancedStats } from "@/components/ui/advanced-stats";

const demoKpis = [
  { label: "Recall @ OP", value: "84.2%", change: "+3.1 pts", status: "up" as const },
  { label: "Holdout precision", value: "91.4%", change: "12,400 rows", status: "neutral" as const },
  { label: "Miss family", value: "mule layering", change: "→ T02", status: "down" as const },
  { label: "Binary AP", value: "76.8%", status: "neutral" as const },
];

const demoChart = [
  { label: "T-4", value: 72 },
  { label: "T-3", value: 75 },
  { label: "T-2", value: 79 },
  { label: "T-1", value: 81 },
  { label: "Now", value: 84 },
];

export default function AdvancedStatsDemo() {
  return (
    <div className="min-h-screen bg-paper-0 px-5 py-8">
      <AdvancedStats
        kpis={demoKpis}
        chartData={demoChart}
        chartTitle="Holdout recall trend"
        chartSubtitle="Defend scoring · lab preview"
        goal={{
          eyebrow: "Operating point",
          title: "Recall target",
          value: 84,
          target: 90,
        }}
        insight={{
          title: "Weakest slice",
          body: (
            <>
              Model misses <span className="font-semibold text-ink">mule layering</span> most often — loop back to T02
              after retrain.
            </>
          ),
        }}
      />
    </div>
  );
}
