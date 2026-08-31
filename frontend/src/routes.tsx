import { Navigate, createBrowserRouter } from "react-router-dom";
import { Shell } from "@/components/layout/Shell";
import { LandingPage } from "@/features/landing/LandingPage";
import { IdentifyLayout } from "@/features/identify/IdentifyLayout";
import { LandscapePage } from "@/features/identify/LandscapePage";
import { DiscoverPage } from "@/features/identify/DiscoverPage";
import { ReviewPage } from "@/features/identify/ReviewPage";
import { GeneratePage } from "@/features/generate/GeneratePage";
import { DefendLayout } from "@/features/defend/DefendLayout";
import { DetectionPage } from "@/features/defend/DetectionPage";
import { InterventionsPage } from "@/features/defend/InterventionsPage";
import { FeedbackPage } from "@/features/defend/FeedbackPage";
import { HyperparametersPage } from "@/features/defend/HyperparametersPage";

export const router = createBrowserRouter([
  { path: "/", element: <LandingPage /> },
  {
    element: <Shell />,
    children: [
      {
        path: "/identify",
        element: <IdentifyLayout />,
        children: [
          { index: true, element: <LandscapePage /> },
          { path: "discover", element: <DiscoverPage /> },
          { path: "review", element: <ReviewPage /> },
        ],
      },
      { path: "/generate", element: <GeneratePage /> },
      { path: "/simulation", element: <Navigate to="/generate" replace /> },
      {
        path: "/defend",
        element: <DefendLayout />,
        children: [
          { index: true, element: <Navigate to="/defend/detection" replace /> },
          { path: "detection", element: <DetectionPage /> },
          { path: "interventions", element: <InterventionsPage /> },
          { path: "feedback", element: <FeedbackPage /> },
          { path: "hyperparameters", element: <HyperparametersPage /> },
        ],
      },
      { path: "/decisioning", element: <Navigate to="/defend/detection" replace /> },
      { path: "/arms-race", element: <Navigate to="/defend/feedback" replace /> },
      { path: "/copilot", element: <Navigate to="/identify" replace /> },
    ],
  },
]);
