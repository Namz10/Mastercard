/** One-shot bus so ⌘K can start recorded Identify after navigating to `/`. */

type Handler = () => void;

const playHandlers = new Set<Handler>();
const skipHandlers = new Set<Handler>();
let pendingPlay = false;

export function requestRecordedIdentify() {
  if (playHandlers.size === 0) {
    pendingPlay = true;
    return;
  }
  playHandlers.forEach((h) => h());
}

export function subscribeRecordedIdentify(handler: Handler) {
  playHandlers.add(handler);
  if (pendingPlay) {
    pendingPlay = false;
    handler();
  }
  return () => {
    playHandlers.delete(handler);
  };
}

export function requestSkipIdentify() {
  skipHandlers.forEach((h) => h());
}

export function subscribeSkipIdentify(handler: Handler) {
  skipHandlers.add(handler);
  return () => {
    skipHandlers.delete(handler);
  };
}
