const STEPS = [
  { path: "/", label: "Threat Map", action: "demo-step-0" },
  { path: "/identify", label: "Identify", action: "demo-step-1" },
  { path: "/simulation", label: "Simulation Console", action: "demo-step-2" },
  { path: "/decisioning", label: "Decisioning", action: "demo-step-3" },
  { path: "/arms-race", label: "Arms Race", action: "demo-step-4" },
  { path: "/copilot", label: "Command Center", action: "demo-step-5" },
] as const;

export { STEPS };

const STORAGE_KEY = "aegisloop-demo-step";

export function readDemoStep(): number {
  const n = Number(sessionStorage.getItem(STORAGE_KEY) ?? "0");
  if (!Number.isFinite(n)) return 0;
  return Math.max(0, Math.min(n, STEPS.length - 1));
}

export function writeDemoStep(next: number): number {
  const clamped = Math.max(0, Math.min(next, STEPS.length - 1));
  sessionStorage.setItem(STORAGE_KEY, String(clamped));
  return clamped;
}

export function useGuidedDemo() {
  const step = readDemoStep();

  return {
    step,
    steps: STEPS,
    next: () => writeDemoStep((step + 1) % STEPS.length),
    reset: () => writeDemoStep(0),
    goTo: (index: number) => writeDemoStep(index),
  };
}
