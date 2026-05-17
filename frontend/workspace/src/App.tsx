import { useEffect } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "./store/auth-store";
import { fetchMe } from "./lib/auth";
import { Shell } from "./components/Shell";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { OverviewPage } from "./pages/OverviewPage";
import { PlaygroundPage } from "./pages/PlaygroundPage";
import { MarketplacePage } from "./pages/MarketplacePage";
import { ModelsPage } from "./pages/ModelsPage";
import { PipelinesPage } from "./pages/PipelinesPage";
import { DeploymentsPage } from "./pages/DeploymentsPage";
import { VaultPage } from "./pages/VaultPage";
import { CompliancePage } from "./pages/CompliancePage";
import { MonitoringPage } from "./pages/MonitoringPage";
import { BillingPage } from "./pages/BillingPage";
import { TeamPage } from "./pages/TeamPage";
import { SettingsPage } from "./pages/SettingsPage";
import { GPCPage } from "./pages/GPCPage";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const status = useAuthStore((s) => s.status);
  if (status === "idle") return null;
  if (status === "unauthenticated") return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  const hydrate = useAuthStore((s) => s.hydrate);
  const status = useAuthStore((s) => s.status);

  useEffect(() => { hydrate(); }, [hydrate]);
  useEffect(() => {
    if (status === "authenticated") void fetchMe().catch(() => undefined);
  }, [status]);

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/" element={<RequireAuth><Shell /></RequireAuth>}>
        <Route index element={<Navigate to="/overview" replace />} />
        <Route path="overview" element={<OverviewPage />} />
        <Route path="playground" element={<PlaygroundPage />} />
        <Route path="marketplace" element={<MarketplacePage />} />
        <Route path="models" element={<ModelsPage />} />
        <Route path="pipelines" element={<PipelinesPage />} />
        <Route path="deployments" element={<DeploymentsPage />} />
        <Route path="vault" element={<VaultPage />} />
        <Route path="compliance" element={<CompliancePage />} />
        <Route path="monitoring" element={<MonitoringPage />} />
        <Route path="billing" element={<BillingPage />} />
        <Route path="team" element={<TeamPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="gpc" element={<GPCPage />} />
      </Route>
    </Routes>
  );
}
