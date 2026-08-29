import { createBrowserRouter } from "react-router-dom";
import { Shell } from "@/components/layout/Shell";
import { ThreatMapPage } from "@/features/threat-map/ThreatMapPage";
import { IdentifyPage } from "@/features/identify/IdentifyPage";
import { SimulationPage } from "@/features/simulation/SimulationPage";
import { DecisioningPage } from "@/features/decisioning/DecisioningPage";
import { ArmsRacePage } from "@/features/arms-race/ArmsRacePage";
import { CopilotPage } from "@/features/copilot/CopilotPage";

export const router = createBrowserRouter([
  {
    element: <Shell />,
    children: [
      { path: "/", element: <ThreatMapPage /> },
      { path: "/identify", element: <IdentifyPage /> },
      { path: "/simulation", element: <SimulationPage /> },
      { path: "/decisioning", element: <DecisioningPage /> },
      { path: "/arms-race", element: <ArmsRacePage /> },
      { path: "/copilot", element: <CopilotPage /> },
    ],
  },
]);
