import { useCallback, useSyncExternalStore } from "react";

type StoreEntry = {
  listeners: Set<() => void>;
  snapshotRaw: string | null;
  snapshotValue: unknown;
};

const stores = new Map<string, StoreEntry>();

function getStore(key: string): StoreEntry {
  let entry = stores.get(key);
  if (!entry) {
    entry = { listeners: new Set(), snapshotRaw: undefined as unknown as null, snapshotValue: undefined };
    stores.set(key, entry);
  }
  return entry;
}

function readRaw(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function notify(key: string) {
  getStore(key).listeners.forEach((listener) => listener());
}

function parse<T>(raw: string | null, initial: T): T {
  if (!raw) return initial;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return initial;
  }
}

/** Stable snapshot per key — useSyncExternalStore requires referential equality when data is unchanged. */
function getCachedSnapshot<T>(key: string, initial: T): T {
  const raw = readRaw(key);
  const entry = getStore(key);
  if (entry.snapshotRaw === raw && entry.snapshotValue !== undefined) {
    return entry.snapshotValue as T;
  }
  const value = parse(raw, initial);
  entry.snapshotRaw = raw;
  entry.snapshotValue = value;
  return value;
}

function invalidateSnapshot(key: string) {
  const entry = stores.get(key);
  if (entry) {
    entry.snapshotRaw = undefined as unknown as null;
    entry.snapshotValue = undefined;
  }
}

export function usePersistedState<T>(key: string, initial: T) {
  const subscribe = useCallback(
    (onStoreChange: () => void) => {
      const entry = getStore(key);
      entry.listeners.add(onStoreChange);
      return () => entry.listeners.delete(onStoreChange);
    },
    [key],
  );

  const getSnapshot = useCallback(() => getCachedSnapshot(key, initial), [key, initial]);

  const state = useSyncExternalStore(subscribe, getSnapshot, () => initial);

  const set = useCallback(
    (value: T | ((prev: T) => T)) => {
      const prev = getCachedSnapshot(key, initial);
      const next = typeof value === "function" ? (value as (p: T) => T)(prev) : value;
      try {
        localStorage.setItem(key, JSON.stringify(next));
      } catch {
        /* storage full/unavailable */
      }
      invalidateSnapshot(key);
      notify(key);
    },
    [key, initial],
  );

  return [state, set] as const;
}

export function clearPersisted(key: string) {
  try {
    localStorage.removeItem(key);
  } catch {
    /* ignore */
  }
  invalidateSnapshot(key);
  notify(key);
}
