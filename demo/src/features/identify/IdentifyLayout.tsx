import { createContext, useContext } from "react";
import { Outlet } from "react-router-dom";
import { useDiscoverStream } from "./useDiscoverStream";
import { useHitlQueue } from "./useIdentify";

type IdentifyStreamContextValue = ReturnType<typeof useDiscoverStream> & {
  hitl: ReturnType<typeof useHitlQueue>;
};

const IdentifyStreamContext = createContext<IdentifyStreamContextValue | null>(null);

export function useIdentifyStream() {
  const ctx = useContext(IdentifyStreamContext);
  if (!ctx) throw new Error("useIdentifyStream must be used within IdentifyLayout");
  return ctx;
}

export function IdentifyLayout() {
  const hitl = useHitlQueue(true);
  const stream = useDiscoverStream(() => void hitl.refetch());
  const value = { ...stream, hitl };

  return (
    <IdentifyStreamContext.Provider value={value}>
      <Outlet />
    </IdentifyStreamContext.Provider>
  );
}
