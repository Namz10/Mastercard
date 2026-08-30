import { Navigate, createBrowserRouter } from "react-router-dom";
import { Shell } from "@/components/layout/Shell";
import { IdentifyPage } from "@/features/identify/IdentifyPage";
import { GeneratePage } from "@/features/generate/GeneratePage";
import { DefendPage } from "@/features/defend/DefendPage";

export const router = createBrowserRouter([
  {
    element: <Shell />,
    children: [
      { path: "/", element: <IdentifyPage /> },
      { path: "/identify", element: <Navigate to="/" replace /> },
      { path: "/generate", element: <GeneratePage /> },
      { path: "/simulation", element: <Navigate to="/generate" replace /> },
      { path: "/defend", element: <DefendPage /> },
      { path: "/decisioning", element: <Navigate to="/defend" replace /> },
      { path: "/arms-race", element: <Navigate to="/defend" replace /> },
      { path: "/copilot", element: <Navigate to="/" replace /> },
    ],
  },
]);
