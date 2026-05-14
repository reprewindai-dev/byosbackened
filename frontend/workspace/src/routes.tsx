import { lazy, Suspense } from "react";
import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { useAuthStore } from "@/store/auth-store";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { useState } from "react";

const LoginPage = lazy(() => import("@/pages/LoginPage").then((m) => ({ default: m.LoginPage })));
const RegisterPage = lazy(() => import("@/pages/RegisterPage").then((m) => ({ default: m.RegisterPage })));
const AcceptInvitePage = lazy(() => import("@/pages/AcceptInvitePage").then((m) => ({ default: m.AcceptInvitePage })));
const GithubCallbackPage = lazy(() => import("@/pages/GithubCallbackPage").then((m) => ({ default: m.GithubCallbackPage })));
const OverviewPage = lazy(() => import("@/pages/OverviewPage").then((m) => ({ default: m.OverviewPage })));
const PlaygroundPage = lazy(() => import("@/pages/PlaygroundPage").then((m) => ({ default: m.PlaygroundPage })));
const MarketplacePage = lazy(() => import("@/pages/MarketplacePage").then((m) => ({ default: m.MarketplacePage })));
const ModelsPage = lazy(() => import("@/pages/ModelsPage").then((m) => ({ default: m.ModelsPage })));
const PipelinesPage = lazy(() => import("@/pages/PipelinesPage").then((m) => ({ default: m.PipelinesPage })));
const DeploymentsPage = lazy(() => import("@/pages/DeploymentsPage").then((m) => ({ default: m.DeploymentsPage })));
const VaultPage = lazy(() => import("@/pages/VaultPage").then((m) => ({ default: m.VaultPage })));
const CompliancePage = lazy(() => import("@/pages/CompliancePage").then((m) => ({ default: m.CompliancePage })));
const MonitoringPage = lazy(() => import("@/pages/MonitoringPage").then((m) => ({ default: m.MonitoringPage })));
const BillingPage = lazy(() => import("@/pages/BillingPage").then((m) => ({ default: m.BillingPage })));
const TeamPage = lazy(() => import("@/pages/TeamPage").then((m) => ({ default: m.TeamPage })));
const SettingsPage = lazy(() => import("@/pages/SettingsPage").then((m) => ({ default: m.SettingsPage })));
const ControlCenterPage = lazy(() => import("@/pages/ControlCenterPage").then((m) => ({ default: m.ControlCenterPage })));
const CompetitiveAdvantagePage = lazy(() => import("@/pages/CompetitiveAdvantagePage").then((m) => ({ default: m.CompetitiveAdvantagePage })));
const UacpPage = lazy(() => import("@/pages/UacpPage").then((m) => ({ default: m.UacpPage })));

// --- NEW: previously unwired router groups ---
const RoutingPage = lazy(() => import("@/pages/RoutingPage").then((m) => ({ default: m.RoutingPage })));
const BudgetPage = lazy(() => import("@/pages/BudgetPage").then((m) => ({ default: m.BudgetPage })));
const SecurityPage = lazy(() => import("@/pages/SecurityPage").then((m) => ({ default: m.SecurityPage })));
const PrivacyPage = lazy(() => import("@/pages/PrivacyPage").then((m) => ({ default: m.PrivacyPage })));
const ContentSafetyPage = lazy(() => import("@/pages/ContentSafetyPage").then((m) => ({ default: m.ContentSafetyPage })));
const InsightsPage = lazy(() => import("@/pages/InsightsPage").then((m) => ({ default: m.InsightsPage })));
const PluginsPage = lazy(() => import("@/pages/PluginsPage").then((m) => ({ default: m.PluginsPage })));
const JobsPage = lazy(() => import("@/pages/JobsPage").then((m) => ({ default: m.JobsPage })));

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.accessToken);
  const status = useAuthStore((s) => s.status);
  if (status === "idle") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-brass border-t-transparent" />
      </div>
    );
  }
  return token ? <>{children}</> : <Navigate to="/login" replace />;
}

function WorkspaceLayout() {
  const [collapsed, setCollapsed] = useState(false);
  return (
    <div className="flex min-h-screen">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="flex-1 overflow-y-auto px-6 py-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function Fallback() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-brass border-t-transparent" />
    </div>
  );
}

export function AppRoutes() {
  return (
    <Suspense fallback={<Fallback />}>
      <Routes>
        {/* Public */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/accept-invite" element={<AcceptInvitePage />} />
        <Route path="/auth/github/callback" element={<GithubCallbackPage />} />

        {/* Protected workspace with sidebar+topbar */}
        <Route element={<RequireAuth><WorkspaceLayout /></RequireAuth>}>
          <Route path="/" element={<Navigate to="/overview" replace />} />
          <Route path="/overview" element={<OverviewPage />} />
          <Route path="/playground" element={<PlaygroundPage />} />
          <Route path="/marketplace" element={<MarketplacePage />} />
          <Route path="/models" element={<ModelsPage />} />
          <Route path="/pipelines" element={<PipelinesPage />} />
          <Route path="/deployments" element={<DeploymentsPage />} />
          <Route path="/vault" element={<VaultPage />} />
          <Route path="/compliance" element={<CompliancePage />} />
          <Route path="/monitoring" element={<MonitoringPage />} />
          <Route path="/billing" element={<BillingPage />} />
          <Route path="/team" element={<TeamPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/control-center" element={<ControlCenterPage />} />
          <Route path="/competitive" element={<CompetitiveAdvantagePage />} />
          <Route path="/uacp" element={<UacpPage />} />
          <Route path="/routing" element={<RoutingPage />} />
          <Route path="/budget" element={<BudgetPage />} />
          <Route path="/security" element={<SecurityPage />} />
          <Route path="/privacy" element={<PrivacyPage />} />
          <Route path="/content-safety" element={<ContentSafetyPage />} />
          <Route path="/insights" element={<InsightsPage />} />
          <Route path="/plugins" element={<PluginsPage />} />
          <Route path="/jobs" element={<JobsPage />} />
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/overview" replace />} />
      </Routes>
    </Suspense>
  );
}
