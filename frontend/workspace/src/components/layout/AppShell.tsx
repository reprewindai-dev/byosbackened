import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Outlet, Navigate, useLocation } from "react-router-dom";
import { TopBar } from "./TopBar";
import { Sidebar } from "./Sidebar";
import { apiRoot } from "@/lib/api";
import { useAuthStore } from "@/store/auth-store";

type StatusPayload = {
  overall_status?: string;
  current_status?: string;
  incidents?: Array<{ id?: string }>;
  maintenance?: Array<{ id?: string }>;
};

export function AppShell() {
  const [collapsed, setCollapsed] = useState(false);
  const status = useAuthStore((s) => s.status);
  const location = useLocation();
  const statusRail = useQuery({
    queryKey: ["shell-status-rail"],
    queryFn: async () => (await apiRoot.get<StatusPayload>("/status/data")).data,
    refetchInterval: 60_000,
    retry: false,
  });

  if (status === "idle") {
    return (
      <div className="flex h-screen items-center justify-center text-muted">
        <div className="animate-pulse font-mono text-[11px] uppercase tracking-widest">Loading workspace...</div>
      </div>
    );
  }

  if (status === "unauthenticated") {
    return <Navigate to="/" state={{ from: location.pathname }} replace />;
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <div className="border-b border-rule bg-ink-1/70 px-6 py-2">
          <div className="flex flex-wrap items-center gap-2 text-[11px] text-bone-2">
            <span className="v-chip v-chip-ok">runtime rail</span>
            <span className="v-chip">
              {statusRail.data?.overall_status ?? statusRail.data?.current_status ?? "operational"}
            </span>
            <span className="v-chip">incidents {statusRail.data?.incidents?.length ?? 0}</span>
            <span className="v-chip">maintenance {statusRail.data?.maintenance?.length ?? 0}</span>
            <span className="font-mono uppercase tracking-[0.12em] text-muted">backend-owned status feed</span>
          </div>
        </div>
        <main className="flex-1 overflow-y-auto px-6 py-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
