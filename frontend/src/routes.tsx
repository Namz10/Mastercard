import { Navigate, createBrowserRouter } from "react-router-dom";
import { Shell } from "@/components/layout/Shell";
import { LandingPage } from "@/features/landing/LandingPage";
import { IdentifyPage } from "@/features/identify/IdentifyPage";
import { GeneratePage } from "@/features/generate/GeneratePage";
import { DefendPage } from "@/features/defend/DefendPage";

export const router = createBrowserRouter([
  { path: "/", element: <LandingPage /> },
  {
    element: <Shell />,
    children: [
      { path: "/identify", element: <IdentifyPage /> },
      { path: "/generate", element: <GeneratePage /> },
      { path: "/simulation", element: <Navigate to="/generate" replace /> },
      { path: "/defend", element: <DefendPage /> },
      { path: "/decisioning", element: <Navigate to="/defend" replace /> },
      { path: "/arms-race", element: <Navigate to="/defend" replace /> },
      { path: "/copilot", element: <Navigate to="/identify" replace /> },
    ],
  },
]);
