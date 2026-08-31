/** Recorded Identify wall clock: 12–18s unless Skip. IMPLEMENTATION-SPEC §7. */

export const RECORDED_MIN_MS = 12_000;
export const RECORDED_MAX_MS = 18_000;

export function scheduleOffsets(
  events: { t?: number }[],
  minMs = RECORDED_MIN_MS,
  maxMs = RECORDED_MAX_MS,
): number[] {
  if (events.length === 0) return [];
  const lastIdx = events.length - 1;
  const raw = events.map((e, i) => {
    if (typeof e.t === "number" && Number.isFinite(e.t)) return Math.max(0, e.t);
    return lastIdx === 0 ? 0 : (i / lastIdx) * minMs;
  });
  const last = raw[raw.length - 1] ?? 0;
  let span = last;
  if (last <= 0) span = minMs;
  else if (last < minMs) span = minMs;
  else if (last > maxMs) span = maxMs;
  const scale = last <= 0 ? 1 : span / last;
  return raw.map((t) => Math.round(t * scale));
}

export function paceEvents<T>(
  events: T[],
  offsetsMs: number[],
  emit: (event: T, index: number) => void,
  signal: AbortSignal,
): Promise<void> {
  return new Promise((resolve) => {
    if (signal.aborted) {
      resolve();
      return;
    }
    const timers: ReturnType<typeof setTimeout>[] = [];
    const started = performance.now();
    const finish = () => {
      timers.forEach(clearTimeout);
      signal.removeEventListener("abort", onAbort);
      resolve();
    };
    const onAbort = () => {
      timers.forEach(clearTimeout);
      signal.removeEventListener("abort", onAbort);
      resolve();
    };
    signal.addEventListener("abort", onAbort);
    if (events.length === 0) {
      finish();
      return;
    }
    events.forEach((event, i) => {
      const wait = Math.max(0, (offsetsMs[i] ?? 0) - (performance.now() - started));
      timers.push(
        setTimeout(() => {
          if (signal.aborted) return;
          emit(event, i);
          if (i === events.length - 1) finish();
        }, wait),
      );
    });
  });
}
