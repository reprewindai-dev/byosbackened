import { useEffect, useState, useCallback } from "react";
import { Search, Flame, CircleDot, Shield } from "lucide-react";
import { useAuthStore } from "@/store/auth-store";
import { api } from "@/lib/api";

interface TopBarStatus {
  status?: string;
  db_ok?: boolean;
  redis_ok?: boolean;
  llm_ok?: boolean;
  circuit_breaker?: { state: string };
}

export function TopBar() {
  const user = useAuthStore((s) => s.user);
  const workspaceName = user?.workspace_name || "workspace";
  const [health, setHealth] = useState<TopBarStatus | null>(null);
  const [balanceUsd, setBalanceUsd] = useState<string | null>(null);

  const fetchLive = useCallback(async () => {
    const results = await Promise.allSettled([
      api.get("/monitoring/health").then(r => r.data).catch(() =>
        fetch(`${window.__VEKLOM_API_BASE__ || ""}/status`).then(r => r.json())
      ),
      api.get("/wallet/balance").then(r => r.data),
    ]);
    if (results[0].status === "fulfilled") setHealth(results[0].value);
    if (results[1].status === "fulfilled") setBalanceUsd(results[1].value?.balance_usd || null);
  }, []);

  useEffect(() => { fetchLive(); const iv = setInterval(fetchLive, 20_000); return () => clearInterval(iv); }, [fetchLive]);

  const isHealthy = health?.status === "healthy" || health?.status === "ok" || (health?.db_ok && health?.redis_ok);
  const cbState = health?.circuit_breaker?.state || "—";

  return (
    <header className="flex h-12 shrink-0 items-center gap-3 border-b border-rule bg-ink-1 px-5">
      {/* Workspace selector */}
      <div className="flex items-center gap-2 rounded-md border border-rule bg-ink-2 px-2.5 py-1">
        <CircleDot className={`h-3 w-3 ${isHealthy ? "text-moss" : "text-amber"}`} />
        <span className="font-mono text-[10px] uppercase tracking-wide text-bone-2">
          {workspaceName}
        </span>
        <span className="text-muted-2">·</span>
        <span className="font-mono text-[10px] text-muted">{cbState !== "—" ? `CB: ${cbState}` : "—"}</span>
      </div>

      {/* Search */}
      <div className="relative ml-2 flex-1 max-w-md">
        <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
        <input
          type="text"
          placeholder="Jump to model, deployment, log, or doc..."
          className="w-full rounded-md border border-rule bg-ink-2 py-1.5 pl-8 pr-8 text-xs text-bone placeholder:text-muted-2 focus:border-brass/50 focus:outline-none"
        />
        <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded border border-rule bg-ink-3 px-1 font-mono text-[9px] text-muted">
          ⌘K
        </kbd>
      </div>

      {/* Right metrics */}
      <div className="ml-auto flex items-center gap-3">
        {/* Reserve balance */}
        <div className="flex items-center gap-1.5 rounded-md border border-rule bg-ink-2 px-2.5 py-1">
          <Flame className="h-3 w-3 text-amber" />
          <span className="font-mono text-[10px] text-bone-2">{balanceUsd ? `$${balanceUsd}` : "—"}</span>
          <span className="text-muted-2">·</span>
          <span className="font-mono text-[10px] text-muted">reserve</span>
        </div>

        {/* Health */}
        <div className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 ${isHealthy ? "border-moss/30 bg-moss/8" : "border-amber/30 bg-amber/8"}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${isHealthy ? "bg-moss" : "bg-amber animate-pulse"}`} />
          <span className={`font-mono text-[10px] uppercase ${isHealthy ? "text-moss" : "text-amber"}`}>{isHealthy ? "Healthy" : health ? "Degraded" : "..."}</span>
        </div>

        {/* LLM */}
        <div className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 ${health?.llm_ok ? "border-electric/30 bg-electric/8" : "border-rule bg-ink-2"}`}>
          <Shield className={`h-3 w-3 ${health?.llm_ok ? "text-electric" : "text-muted"}`} />
          <span className={`font-mono text-[10px] uppercase ${health?.llm_ok ? "text-electric" : "text-muted"}`}>{health?.llm_ok ? "LLM Online" : "LLM —"}</span>
        </div>
      </div>
    </header>
  );
}
