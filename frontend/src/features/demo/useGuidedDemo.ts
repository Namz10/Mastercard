const STEPS = [
  { path: "/identify", label: "Seed Atlas", action: "demo-step-0" },
  { path: "/identify", label: "Enter topic, run research, approve a vector", action: "demo-step-1" },
  { path: "/simulation", label: "Run population", action: "demo-step-2" },
  { path: "/decisioning", label: "Defend: fit model", action: "demo-step-3" },
  { path: "/decisioning", label: "Inspect score + brake", action: "demo-step-4" },
  { path: "/arms-race", label: "Run Loop M once", action: "demo-step-5" },
] as const;

export { STEPS };

export function useGuidedDemo() {
  const storageKey = "aegisloop-demo-step";
  const step = Number(sessionStorage.getItem(storageKey) ?? "0");

  const setStep = (next: number) => {
    sessionStorage.setItem(storageKey, String(Math.max(0, Math.min(next, STEPS.length - 1))));
  };

  return {
    step,
    steps: STEPS,
    next: () => setStep(step + 1),
    reset: () => setStep(0),
    goTo: (index: number) => setStep(index),
  };
}
