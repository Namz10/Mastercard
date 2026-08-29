import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { router } from "./routes";
import { queryClient } from "@/lib/query-client";
import { LatestRunProvider } from "@/lib/latest-run-context";
import "@/styles/tokens.css";
import "@/styles/globals.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <LatestRunProvider>
        <RouterProvider router={router} />
      </LatestRunProvider>
    </QueryClientProvider>
  </StrictMode>,
);
