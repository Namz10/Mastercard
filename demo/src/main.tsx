import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { router } from "./routes";
import { queryClient } from "@/lib/query-client";
import { SessionProvider } from "@/lib/session-store";
import { NarrationProvider } from "@/explain/NarrationContext";
import { Teleprompter } from "@/explain/Teleprompter";
import "@/styles/tokens.css";
import "@/styles/globals.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <SessionProvider>
        <NarrationProvider>
          <RouterProvider router={router} />
          <Teleprompter />
        </NarrationProvider>
      </SessionProvider>
    </QueryClientProvider>
  </StrictMode>,
);
