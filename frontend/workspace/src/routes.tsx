import { Routes, Route, Navigate } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { AcceptInvitePage } from "./pages/AcceptInvitePage";
import { ControlCenterPage } from "./pages/ControlCenterPage";
import { OverviewPage } from "./pages/OverviewPage";
import { PlaygroundPage } from "./pages/PlaygroundPage";
import { MarketplacePage } from "./pages/MarketplacePage";
import { BillingPage } from "./pages/BillingPage";
import { SettingsPage } from "./pages/SettingsPage";
import { MonitoringPage } from "./pages/MonitoringPage";
import { VaultPage } from "./pages/VaultPage";
import { TeamPage } from "./pages/TeamPage";
import { CompliancePage } from "./pages/CompliancePage";
import { ModelsPage } from "./pages/ModelsPage";
import { PipelinesPage } from "./pages/PipelinesPage";
import { DeploymentsPage } from "./pages/DeploymentsPage";

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/accept-invite" element={<AcceptInvitePage />} />

      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/overview" replace />} />
        <Route path="/dashboard" element={<ControlCenterPage />} />
        <Route path="/control-center" element={<ControlCenterPage />} />
        <Route path="/overview" element={<OverviewPage />} />
        <Route path="/playground" element={<PlaygroundPage />} />
        <Route path="/marketplace" element={<MarketplacePage />} />
        <Route path="/marketplace/:slug" element={<MarketplacePage />} />
        <Route path="/models" element={<ModelsPage />} />
        <Route path="/pipelines" element={<PipelinesPage />} />
        <Route path="/deployments" element={<DeploymentsPage />} />
        <Route path="/vault" element={<VaultPage />} />
        <Route path="/compliance" element={<CompliancePage />} />
        <Route path="/monitoring" element={<MonitoringPage />} />
        <Route path="/billing" element={<BillingPage />} />
        <Route path="/team" element={<TeamPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/overview" replace />} />
    </Routes>
  );
}
