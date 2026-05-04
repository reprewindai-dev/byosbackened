import { Bell, BookOpen, Command, Key, Search } from "lucide-react";
import { useAuthStore } from "@/store/auth-store";

export function TopBar() {
  const user = useAuthStore((s) => s.user);
  const workspaceLabel = user?.workspace_name ?? user?.workspace_id ?? "workspace";
  const regionLabel = user?.region ?? "region-unset";
  const planLabel = user?.plan ?? "plan-unset";
  const initials = (user?.name ?? user?.email ?? "VK")
    .split(/[\s@]/)
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase() ?? "")
    .join("");

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
          placeholder="Jump to model, deployment, log, or doc..."
        />
        <span className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-1 rounded border border-rule-2 bg-ink-2 px-1.5 py-0.5 font-mono text-[10px] text-muted">
          <Command className="h-3 w-3" />K
        </span>
      </div>

      <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.1em]">
        <span className="v-chip">Operating reserve</span>
        <span className="v-chip">Event-based billing</span>
        <span className="v-chip v-chip-ok">live backend</span>
        <span className="v-chip v-chip-brass">EU-sovereign</span>
      </div>

      <div className="flex items-center gap-1 pl-2">
        <button className="rounded-md p-1.5 text-muted hover:bg-white/5 hover:text-bone" aria-label="Docs">
          <BookOpen className="h-4 w-4" />
        </button>
        <button className="rounded-md p-1.5 text-muted hover:bg-white/5 hover:text-bone" aria-label="API keys">
          <Key className="h-4 w-4" />
        </button>
        <button className="rounded-md p-1.5 text-muted hover:bg-white/5 hover:text-bone" aria-label="Notifications">
          <Bell className="h-4 w-4" />
        </button>
        <div className="ml-2 flex h-7 w-7 items-center justify-center rounded-md bg-brass/20 font-mono text-[11px] font-semibold text-brass-2">
          {initials || "VK"}
        </div>
      </div>
    </header>
  );
}
