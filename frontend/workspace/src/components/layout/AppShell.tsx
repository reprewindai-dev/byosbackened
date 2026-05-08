import { useState } from "react";
import { Outlet, Navigate, useLocation } from "react-router-dom";
import { TopBar } from "./TopBar";
import { Sidebar } from "./Sidebar";
import { useAuthStore } from "@/store/auth-store";

export function AppShell() {
  const [collapsed, setCollapsed] = useState(false);
  const status = useAuthStore((s) => s.status);
  const location = useLocation();
  const isOverviewCenter = location.pathname === "/overview";

  if (status === "idle") {
    return (
      <div className="flex h-screen items-center justify-center text-muted">
        <div className="animate-pulse font-mono text-[11px] uppercase tracking-widest">Loading workspace…</div>
      </div>
    );
  }

  if (status === "unauthenticated") {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  if (isOverviewCenter) {
    return (
      <main className="command-center-stage">
        <Outlet />
      </main>
    );
  }

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
