import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Bell, BookOpen, Command, Key, Search } from "lucide-react";
import { api } from "@/lib/api";
import { fmtCents } from "@/lib/cn";
import { useAuthStore } from "@/store/auth-store";
import type { OverviewPayload } from "@/types/api";

interface WalletBalance {
  balance: number;
  monthly_credits_included: number;
  monthly_credits_used: number;
}

const JUMP_ROUTES = [
  { label: "overview", to: "/overview" },
  { label: "dashboard", to: "/overview" },
  { label: "playground", to: "/playground" },
  { label: "marketplace", to: "/marketplace" },
  { label: "models", to: "/models" },
  { label: "pipelines", to: "/pipelines" },
  { label: "deployments", to: "/deployments" },
  { label: "vault", to: "/vault" },
  { label: "api keys", to: "/vault" },
  { label: "compliance", to: "/compliance" },
  { label: "monitoring", to: "/monitoring" },
  { label: "billing", to: "/billing" },
  { label: "team", to: "/team" },
  { label: "settings", to: "/settings" },
];

export function TopBar() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const [jump, setJump] = useState("");
  const overview = useQuery({
    queryKey: ["topbar-overview"],
    queryFn: async () => (await api.get<OverviewPayload>("/monitoring/overview")).data,
    refetchInterval: 30_000,
    retry: false,
  });
  const wallet = useQuery({
    queryKey: ["topbar-wallet"],
    queryFn: async () => (await api.get<WalletBalance>("/wallet/balance")).data,
    refetchInterval: 30_000,
    retry: false,
  });

  const displayName = user?.full_name ?? user?.name ?? user?.email ?? "Veklom";
  const initials = displayName
    .split(/[\s@]/)
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase() ?? "")
    .join("");
  const workspaceLabel = user?.workspace_name?.trim() || "Workspace";
  const regionLabel = user?.region?.trim() || "tenant-scoped";
  const planLabel = (user?.plan ?? user?.role ?? "live").replace(/_/g, " ");
  const burnCents = overview.data?.spend?.burn_rate_per_min_cents;
  const budgetPct = useMemo(() => {
    const included = wallet.data?.monthly_credits_included ?? 0;
    if (included > 0) return Math.round(((wallet.data?.monthly_credits_used ?? 0) / included) * 100);
    return overview.data?.spend?.forecast_cap_pct;
  }, [overview.data?.spend?.forecast_cap_pct, wallet.data]);
  const degraded = overview.isError || wallet.isError;

  const submitJump = () => {
    const q = jump.trim().toLowerCase();
    if (!q) return;
    const route = JUMP_ROUTES.find((r) => r.label.includes(q) || q.includes(r.label));
    if (route) {
      navigate(route.to);
      setJump("");
    }
  };

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-rule bg-ink/80 px-4 backdrop-blur-md">
      <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.12em] text-bone-2">
        <span className="v-chip">
          <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-moss shadow-moss-glow" />
          {workspaceLabel}
        </span>
        <span className="v-chip">{regionLabel}</span>
        <span className="v-chip">{planLabel}</span>
      </div>

      <div className="relative mx-2 flex-1 max-w-xl">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
        <input
          className="v-input pl-9 pr-14 text-[13px]"
          value={jump}
          onChange={(e) => setJump(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") submitJump();
          }}
          placeholder="Jump to model, deployment, log, or doc..."
        />
        <button
          className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-1 rounded border border-rule-2 bg-ink-2 px-1.5 py-0.5 font-mono text-[10px] text-muted hover:text-bone"
          onClick={submitJump}
          type="button"
        >
          <Command className="h-3 w-3" />K
        </button>
      </div>

      <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.1em]">
        <span className="v-chip">
          Burn <span className="text-bone">{burnCents != null ? fmtCents(burnCents) : "--"}</span>/min
        </span>
        <span className="v-chip">
          <span className="text-amber">{budgetPct != null ? `${budgetPct}%` : "--"}</span> budget
        </span>
        <span className={degraded ? "v-chip v-chip-warn" : "v-chip v-chip-ok"}>
          {degraded ? "degraded" : "healthy"}
        </span>
        <span className="v-chip v-chip-brass">tenant-scoped</span>
      </div>

      <div className="flex items-center gap-1 pl-2">
        <button
          className="rounded-md p-1.5 text-muted hover:bg-white/5 hover:text-bone"
          aria-label="Docs"
          onClick={() => {
            window.location.href = "/docs/";
          }}
        >
          <BookOpen className="h-4 w-4" />
        </button>
        <button
          className="rounded-md p-1.5 text-muted hover:bg-white/5 hover:text-bone"
          aria-label="API keys"
          onClick={() => navigate("/vault")}
        >
          <Key className="h-4 w-4" />
        </button>
        <button
          className="rounded-md p-1.5 text-muted hover:bg-white/5 hover:text-bone"
          aria-label="Notifications"
          onClick={() => navigate("/monitoring")}
        >
          <Bell className="h-4 w-4" />
        </button>
        <div className="ml-2 flex h-7 w-7 items-center justify-center rounded-md bg-brass/20 font-mono text-[11px] font-semibold text-brass-2">
          {initials || "VK"}
        </div>
      </div>
    </header>
  );
}
