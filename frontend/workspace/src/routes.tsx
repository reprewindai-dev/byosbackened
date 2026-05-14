import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";

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
  return token ? <>{children}</> : <Navigate to="/login" replace />;
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

        {/* Protected workspace */}
        <Route path="/" element={<RequireAuth><Navigate to="/overview" replace /></RequireAuth>} />
        <Route path="/overview" element={<RequireAuth><OverviewPage /></RequireAuth>} />
        <Route path="/playground" element={<RequireAuth><PlaygroundPage /></RequireAuth>} />
        <Route path="/marketplace" element={<RequireAuth><MarketplacePage /></RequireAuth>} />
        <Route path="/models" element={<RequireAuth><ModelsPage /></RequireAuth>} />
        <Route path="/pipelines" element={<RequireAuth><PipelinesPage /></RequireAuth>} />
        <Route path="/deployments" element={<RequireAuth><DeploymentsPage /></RequireAuth>} />
        <Route path="/vault" element={<RequireAuth><VaultPage /></RequireAuth>} />
        <Route path="/compliance" element={<RequireAuth><CompliancePage /></RequireAuth>} />
        <Route path="/monitoring" element={<RequireAuth><MonitoringPage /></RequireAuth>} />
        <Route path="/billing" element={<RequireAuth><BillingPage /></RequireAuth>} />
        <Route path="/team" element={<RequireAuth><TeamPage /></RequireAuth>} />
        <Route path="/settings" element={<RequireAuth><SettingsPage /></RequireAuth>} />

        {/* Superuser / internal */}
        <Route path="/control-center" element={<RequireAuth><ControlCenterPage /></RequireAuth>} />
        <Route path="/competitive" element={<RequireAuth><CompetitiveAdvantagePage /></RequireAuth>} />
        <Route path="/uacp" element={<RequireAuth><UacpPage /></RequireAuth>} />

        {/* NEW routes — previously 0% wired */}
        <Route path="/routing" element={<RequireAuth><RoutingPage /></RequireAuth>} />
        <Route path="/budget" element={<RequireAuth><BudgetPage /></RequireAuth>} />
        <Route path="/security" element={<RequireAuth><SecurityPage /></RequireAuth>} />
        <Route path="/privacy" element={<RequireAuth><PrivacyPage /></RequireAuth>} />
        <Route path="/content-safety" element={<RequireAuth><ContentSafetyPage /></RequireAuth>} />
        <Route path="/insights" element={<RequireAuth><InsightsPage /></RequireAuth>} />
        <Route path="/plugins" element={<RequireAuth><PluginsPage /></RequireAuth>} />
        <Route path="/jobs" element={<RequireAuth><JobsPage /></RequireAuth>} />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/overview" replace />} />
      </Routes>
    </Suspense>
  );
}
