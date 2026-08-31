export type SpeedMode = "instant" | "fast" | "presenter" | "booth";

export function parseSpeedMode(): SpeedMode {
  const q = new URLSearchParams(window.location.search).get("speed");
  if (q === "instant" || q === "0") return "instant";
  if (q === "fast") return "fast";
  if (q === "presenter") return "presenter";
  const env = import.meta.env.VITE_DEMO_SPEED;
  if (env === "0" || env === "instant") return "instant";
  if (env === "fast") return "fast";
  if (env === "presenter") return "presenter";
  return "booth";
}

export function timingScale(mode: SpeedMode): number {
  switch (mode) {
    case "instant":
      return 0;
    case "fast":
      return 0.08;
    case "presenter":
      return 0.35;
    default:
      return 0.25;
  }
}

export function captionPauseMs(mode: SpeedMode): number {
  if (mode === "instant" || mode === "fast") return 0;
  if (mode === "presenter") return 1800;
  return 1200;
}

export function captionsEnabled(mode: SpeedMode): boolean {
  if (mode === "presenter") return true;
  const q = new URLSearchParams(window.location.search).get("captions");
  if (q === "0" || q === "false") return false;
  if (q === "1" || q === "true") return true;
  return mode !== "instant";
}
