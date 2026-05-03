import { Routes, Route, Navigate } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { LoginPage } from "./pages/LoginPage";
import { OverviewPage } from "./pages/OverviewPage";
import { PlaceholderPage } from "./pages/PlaceholderPage";
import { PlaygroundPage } from "./pages/PlaygroundPage";
import { MarketplacePage } from "./pages/MarketplacePage";
import { BillingPage } from "./pages/BillingPage";
import { SettingsPage } from "./pages/SettingsPage";

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/overview" replace />} />
        <Route path="/overview" element={<OverviewPage />} />
        <Route path="/playground" element={<PlaygroundPage />} />
        <Route path="/marketplace" element={<MarketplacePage />} />
        <Route
          path="/models"
          element={<PlaceholderPage title="Models" subtitle="Deployed models across Hetzner primary and AWS burst." />}
        />
        <Route
          path="/pipelines"
          element={<PlaceholderPage title="Pipelines" subtitle="Governed execution pipelines." />}
        />
        <Route
          path="/deployments"
          element={<PlaceholderPage title="Deployments" subtitle="Active deployments and canary status." />}
        />
        <Route
          path="/vault"
          element={<PlaceholderPage title="Sovereign secret store" subtitle="AES-256 at rest, TLS in transit, runtime injection only." />}
        />
        <Route
          path="/compliance"
          element={<PlaceholderPage title="Compliance" subtitle="Framework coverage, evidence schedules, signed exports." />}
        />
        <Route
          path="/monitoring"
          element={<PlaceholderPage title="Monitoring" subtitle="Metrics, alerts, security events." />}
        />
        <Route path="/billing" element={<BillingPage />} />
        <Route
          path="/team"
          element={<PlaceholderPage title="Team & access" subtitle="Roles, MFA, sessions, SAML / SCIM." />}
        />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/overview" replace />} />
    </Routes>
  );
}
