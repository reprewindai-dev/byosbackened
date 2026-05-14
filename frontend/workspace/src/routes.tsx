import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import type { ReactNode } from "react";
import { AppShell } from "./components/layout/AppShell";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { GithubCallbackPage } from "./pages/GithubCallbackPage";
import { AcceptInvitePage } from "./pages/AcceptInvitePage";
import { ControlCenterPage } from "./pages/ControlCenterPage";
import { OverviewPage } from "./pages/OverviewPage";
import { UacpPage } from "./pages/UacpPage";
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
import { CompetitiveAdvantagePage } from "./pages/CompetitiveAdvantagePage";
import { useAuthStore } from "@/store/auth-store";

function SuperuserOnly({ children }: { children: ReactNode }) {
  const user = useAuthStore((s) => s.user);
  return user?.is_superuser ? <>{children}</> : <Navigate to="/overview" replace />;
}

function HomeRoute() {
  return <Navigate to="/overview" replace />;
}

function OverviewRoute() {
  return <OverviewPage />;
}

function MfaProtected({ children }: { children: ReactNode }) {
  const user = useAuthStore((s) => s.user);
  const location = useLocation();
  if (!user?.mfa_enabled) {
    return <Navigate to="/team" replace state={{ from: location.pathname, mfaRequired: true }} />;
  }
  return <>{children}</>;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/auth/github/callback" element={<GithubCallbackPage />} />
      <Route path="/accept-invite" element={<AcceptInvitePage />} />

      <Route element={<AppShell />}>
        <Route index element={<HomeRoute />} />
        <Route path="/dashboard" element={<MfaProtected><SuperuserOnly><ControlCenterPage /></SuperuserOnly></MfaProtected>} />
        <Route path="/control-center" element={<MfaProtected><SuperuserOnly><ControlCenterPage /></SuperuserOnly></MfaProtected>} />
        <Route path="/overview" element={<OverviewRoute />} />
        <Route path="/uacp" element={<UacpPage />} />
        <Route path="/playground" element={<PlaygroundPage />} />
        <Route path="/marketplace" element={<MarketplacePage />} />
        <Route path="/marketplace/:slug" element={<MarketplacePage />} />
        <Route path="/models" element={<ModelsPage />} />
        <Route path="/pipelines" element={<PipelinesPage />} />
        <Route path="/deployments" element={<DeploymentsPage />} />
        <Route path="/vault" element={<MfaProtected><VaultPage /></MfaProtected>} />
        <Route path="/compliance" element={<CompliancePage />} />
        <Route path="/monitoring" element={<MonitoringPage />} />
        <Route path="/billing" element={<MfaProtected><BillingPage /></MfaProtected>} />
        <Route path="/team" element={<TeamPage />} />
        <Route path="/settings" element={<MfaProtected><SettingsPage /></MfaProtected>} />
        <Route path="/advantage" element={<CompetitiveAdvantagePage />} />
      </Route>

      <Route path="*" element={<HomeRoute />} />
    </Routes>
  );
}
