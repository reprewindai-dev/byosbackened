import { Search, Flame, CircleDot, Shield } from "lucide-react";
import { useAuthStore } from "@/store/auth-store";

export function TopBar() {
  const user = useAuthStore((s) => s.user);
  const workspaceName = user?.workspace_name || "workspace";

  return (
    <header className="flex h-12 shrink-0 items-center gap-3 border-b border-rule bg-ink-1 px-5">
      {/* Workspace selector */}
      <div className="flex items-center gap-2 rounded-md border border-rule bg-ink-2 px-2.5 py-1">
        <CircleDot className="h-3 w-3 text-moss" />
        <span className="font-mono text-[10px] uppercase tracking-wide text-bone-2">
          {workspaceName}
        </span>
        <span className="text-muted-2">·</span>
        <span className="font-mono text-[10px] text-muted">US-East</span>
        <span className="text-muted-2">·</span>
        <span className="font-mono text-[10px] text-muted">V1.42.0</span>
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
        {/* Burn rate */}
        <div className="flex items-center gap-1.5 rounded-md border border-rule bg-ink-2 px-2.5 py-1">
          <Flame className="h-3 w-3 text-amber" />
          <span className="font-mono text-[10px] text-bone-2">$0.0154/min</span>
          <span className="text-muted-2">·</span>
          <span className="font-mono text-[10px] text-muted">66% budget</span>
        </div>

        {/* Health */}
        <div className="flex items-center gap-1.5 rounded-full border border-moss/30 bg-moss/8 px-2.5 py-1">
          <span className="h-1.5 w-1.5 rounded-full bg-moss" />
          <span className="font-mono text-[10px] uppercase text-moss">Healthy</span>
        </div>

        {/* Region */}
        <div className="flex items-center gap-1.5 rounded-full border border-electric/30 bg-electric/8 px-2.5 py-1">
          <Shield className="h-3 w-3 text-electric" />
          <span className="font-mono text-[10px] uppercase text-electric">EU-Sovereign</span>
        </div>
      </div>
    </header>
  );
}
