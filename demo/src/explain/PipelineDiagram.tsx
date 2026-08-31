import clsx from "clsx";

const FIT_STEPS = [
  "Load",
  "Rules",
  "Folds",
  "Inner HGB",
  "Inner-val OP",
  "IsoForest",
  "Outer HGB",
  "Calibrate",
  "Permutation",
  "Bootstrap",
  "Brake",
  "Persist",
];

const GENERATE_STEPS = [
  "Quiet world",
  "Customer traffic",
  "Inject families",
  "Fidelity PSI",
  "Persist ledger",
];

const LOOP_STEPS = [
  "Miss family",
  "Extra mix",
  "New gtest",
  "Refit parent",
  "Refit augmented",
  "Score before/after",
];

const IDENTIFY_STEPS = ["Collect", "Extract", "Ground", "Rank", "HITL"];

function stepIndex(verb: string | undefined, body: string | undefined, mode: string): number {
  const b = (body ?? "").toLowerCase();
  if (mode === "fit") {
    if (b.includes("load")) return 0;
    if (b.includes("rule")) return 1;
    if (b.includes("fold")) return 2;
    if (b.includes("train detector") || b.includes("inner")) return 3;
    if (b.includes("threshold") || b.includes("validation")) return 4;
    if (b.includes("isolation")) return 5;
    if (b.includes("outer")) return 6;
    if (b.includes("calibrat")) return 7;
    if (b.includes("permutation") || b.includes("moved")) return 8;
    if (b.includes("bootstrap") || b.includes("stability")) return 9;
    if (b.includes("histogram") || b.includes("policy")) return 10;
    if (b.includes("persist") || b.includes("complete")) return 11;
    return 3;
  }
  if (mode === "generate") {
    if (b.includes("quiet")) return 0;
    if (b.includes("customer") || b.includes("traffic")) return 1;
    if (b.includes("inject") || b.includes("overlay") || b.includes("mule")) return 2;
    if (b.includes("psi") || b.includes("fidelity")) return 3;
    if (b.includes("parquet") || b.includes("committed")) return 4;
    return 0;
  }
  if (mode === "loop") {
    if (b.includes("miss")) return 0;
    if (b.includes("extra")) return 1;
    if (b.includes("gtest")) return 2;
    if (b.includes("refit parent")) return 3;
    if (b.includes("refit") && !b.includes("parent")) return 4;
    if (b.includes("score") || b.includes("complete")) return 5;
    return 0;
  }
  if (mode === "identify") {
    if (verb === "COLLECT") return 0;
    if (verb === "EXTRACT") return 1;
    if (verb === "GROUND") return 2;
    if (verb === "RANK") return 3;
    if (verb === "PROPOSE" || verb === "REPLAY") return 4;
    return 0;
  }
  return 0;
}

export function PipelineDiagram({
  mode,
  activeVerb,
  activeBody,
  className,
}: {
  mode: "fit" | "generate" | "loop" | "identify";
  activeVerb?: string;
  activeBody?: string;
  className?: string;
}) {
  const steps =
    mode === "fit"
      ? FIT_STEPS
      : mode === "generate"
        ? GENERATE_STEPS
        : mode === "loop"
          ? LOOP_STEPS
          : IDENTIFY_STEPS;
  const active = stepIndex(activeVerb, activeBody, mode);

  return (
    <div className={clsx("flex flex-wrap gap-1", className)} data-demo="pipeline-diagram">
      {steps.map((label, i) => (
        <div
          key={label}
          className={clsx(
            "text-[10px] px-2 py-1 rounded-sm border font-medium transition-colors",
            i < active
              ? "bg-sage-100 border-sage-600/30 text-sage-700"
              : i === active
                ? "bg-sage-600 text-paper-1 border-sage-600 animate-pulse"
                : "bg-paper-1 border-border text-ink-faint",
          )}
        >
          {i < active ? "✓ " : ""}{label}
        </div>
      ))}
    </div>
  );
}
