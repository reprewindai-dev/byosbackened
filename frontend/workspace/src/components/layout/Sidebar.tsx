import { NavLink } from "react-router-dom";
import {
  Activity,
  Box,
  ChevronLeft,
  CircuitBoard,
  CreditCard,
  FileCheck2,
  Gauge,
  KeyRound,
  LineChart,
  Settings2,
  ShieldCheck,
  ShoppingBag,
  TerminalSquare,
  Users,
} from "lucide-react";
import { cn } from "@/lib/cn";

interface NavItem {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
}

const CUSTOMER_SECTIONS: { title?: string; items: NavItem[] }[] = [
  {
    title: "Workspace",
    items: [
      { to: "/overview", label: "Overview", icon: Gauge },
      { to: "/playground", label: "Playground", icon: TerminalSquare, badge: "LIVE" },
      { to: "/marketplace", label: "Marketplace", icon: ShoppingBag },
    ],
  },
  {
    title: "Infrastructure",
    items: [
      { to: "/models", label: "Models", icon: Box },
      { to: "/pipelines", label: "Pipelines", icon: CircuitBoard },
      { to: "/deployments", label: "Endpoints", icon: Gauge },
    ],
  },
  {
    title: "Governance",
    items: [
      { to: "/vault", label: "Vault", icon: KeyRound },
      { to: "/compliance", label: "Compliance", icon: FileCheck2 },
    ],
  },
  {
    title: "Operations",
    items: [
      { to: "/monitoring", label: "Monitoring", icon: LineChart },
      { to: "/billing", label: "Billing", icon: CreditCard },
    ],
  },
  {
    title: "Access",
    items: [
      { to: "/team", label: "Team", icon: Users },
      { to: "/settings", label: "Settings", icon: Settings2 },
    ],
  },
];

export function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  return (
    <aside
      className={cn(
        "sticky top-0 flex h-screen shrink-0 flex-col border-r border-rule bg-ink-1/70 backdrop-blur-md transition-all",
        collapsed ? "w-14" : "w-60",
      )}
    >
      <div className="flex h-14 items-center justify-between border-b border-rule px-3">
        <NavLink to="/overview" className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-brass/20 font-mono text-[11px] font-bold text-brass-2">
            V
          </div>
          {!collapsed && (
            <div className="flex flex-col leading-none">
              <span className="text-[13px] font-semibold tracking-tight">Veklom</span>
              <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-muted">sovereign control node</span>
            </div>
          )}
        </NavLink>
        <button
          onClick={onToggle}
          className="rounded p-1 text-muted hover:bg-white/5 hover:text-bone"
          aria-label="Toggle sidebar"
        >
          <ChevronLeft className={cn("h-4 w-4 transition-transform", collapsed && "rotate-180")} />
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto py-2">
        {CUSTOMER_SECTIONS.map((section) => (
          <div key={section.title ?? section.items.map((item) => item.to).join("-")} className="px-2">
            {!collapsed && section.title && <div className="v-sidebar-section">{section.title}</div>}
            {section.items.map(({ to, label, icon: Icon, badge }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  cn("v-sidebar-item", isActive && "v-sidebar-item-active", collapsed && "justify-center")
                }
                title={collapsed ? label : undefined}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {!collapsed && (
                  <>
                    <span className="flex-1 truncate">{label}</span>
                    {badge && (
                      <span className="font-mono text-[9px] font-semibold uppercase tracking-wider text-moss">
                        {badge}
                      </span>
                    )}
                  </>
                )}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      {!collapsed && (
        <div className="m-3 rounded-lg border border-rule p-3 text-[11px] text-bone-2">
          <div className="mb-2 flex items-center justify-between font-mono uppercase tracking-[0.12em]">
            <span className="text-muted">Sovereign Mode</span>
            <span className="inline-flex items-center gap-1 text-moss">
              <Activity className="h-3 w-3" />
              ON-PREM
            </span>
          </div>
          <p className="text-[11px] leading-relaxed text-muted">
            All requests evaluated by policy on Hetzner. AWS burst gated by tenant rule.
          </p>
          <div className="mt-2 flex gap-1.5">
            <span className="rounded border border-brass/30 bg-brass/10 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-brass-2">
              Hetzner
            </span>
            <span className="rounded border border-electric/30 bg-electric/10 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-electric">
              AWS
            </span>
          </div>
        </div>
      )}

      {!collapsed && (
        <div className="border-t border-rule px-3 py-2 text-[10px] text-muted">
          <ShieldCheck className="mr-1 inline h-3 w-3" />
          mTLS internal - v1.42.0
        </div>
      )}
    </aside>
  );
}
