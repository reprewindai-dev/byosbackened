import { NavLink } from "react-router-dom";
import { cn } from "@/lib/cn";
import {
  LayoutDashboard,
  TerminalSquare,
  Store,
  Cpu,
  Workflow,
  Rocket,
  KeyRound,
  ShieldCheck,
  Activity,
  CreditCard,
  Users,
  Server,
  Cloudy,
  Bot,
  Settings,
} from "lucide-react";

const NAV_GROUPS = [
  {
    label: "Workspace",
    items: [
      { to: "/overview", icon: LayoutDashboard, label: "Overview" },
      { to: "/playground", icon: TerminalSquare, label: "Playground", badge: "LIVE" },
      { to: "/marketplace", icon: Store, label: "Marketplace" },
    ],
  },
  {
    label: "Infrastructure",
    items: [
      { to: "/models", icon: Cpu, label: "Models" },
      { to: "/pipelines", icon: Workflow, label: "Pipelines" },
      { to: "/deployments", icon: Rocket, label: "Deployments" },
    ],
  },
  {
    label: "Governance",
    items: [
      { to: "/vault", icon: KeyRound, label: "Vault" },
      { to: "/compliance", icon: ShieldCheck, label: "Compliance" },
    ],
  },
  {
    label: "Operations",
    items: [
      { to: "/monitoring", icon: Activity, label: "Monitoring" },
      { to: "/billing", icon: CreditCard, label: "Billing" },
      { to: "/team", icon: Users, label: "Team" },
      { to: "/settings", icon: Settings, label: "Settings" },
    ],
  },
  {
    label: "Control Plane",
    items: [
      { to: "/gpc", icon: Bot, label: "GPC Terminal", badge: "UACP" },
    ],
  },
];

export function Sidebar() {
  return (
    <aside className="flex w-[200px] shrink-0 flex-col border-r border-rule bg-ink-1">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 py-4">
        <svg viewBox="0 0 32 32" className="h-7 w-7 shrink-0">
          <path
            d="M16 4 L6 24 L10 24 L16 13 L22 24 L26 24 Z"
            fill="#e5a832"
          />
          <circle cx="16" cy="20" r="2.5" fill="#e5a832" />
        </svg>
        <div className="leading-none">
          <span className="text-sm font-bold tracking-tight text-bone">Veklom</span>
          <span className="mt-0.5 block font-mono text-[8px] uppercase tracking-[0.15em] text-muted">
            sovereign control node
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-2">
        {NAV_GROUPS.map((group) => (
          <div key={group.label} className="mb-4">
            <div className="mb-1.5 px-2 font-mono text-[9px] uppercase tracking-[0.14em] text-muted-2">
              {group.label}
            </div>
            {group.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    "group flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-[13px] font-medium transition-colors",
                    isActive
                      ? "bg-brass/10 text-brass-2"
                      : "text-bone/70 hover:bg-ink-3 hover:text-bone",
                  )
                }
              >
                <item.icon className="h-4 w-4 shrink-0 opacity-70 group-hover:opacity-100" />
                <span>{item.label}</span>
                {item.badge && (
                  <span className="ml-auto rounded bg-moss/15 px-1.5 py-0.5 font-mono text-[9px] text-moss">
                    {item.badge}
                  </span>
                )}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      {/* Footer — Sovereign Mode */}
      <div className="border-t border-rule px-4 py-3">
        <div className="flex items-center gap-1.5">
          <span className="v-section-label">Sovereign Mode</span>
          <span className="ml-auto flex items-center gap-1">
            <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-moss" />
            <span className="font-mono text-[9px] uppercase text-moss">on-prem</span>
          </span>
        </div>
        <p className="mt-1.5 text-[10px] leading-relaxed text-muted-2">
          All requests evaluated by policy on Hetzner. AWS burst gated by tenant rule.
        </p>
        <div className="mt-2 flex gap-1.5">
          <span className="rounded bg-amber/15 px-1.5 py-0.5 font-mono text-[9px] text-amber">
            <Server className="mr-0.5 inline h-2.5 w-2.5" />
            Hetzner
          </span>
          <span className="rounded bg-electric/15 px-1.5 py-0.5 font-mono text-[9px] text-electric">
            <Cloudy className="mr-0.5 inline h-2.5 w-2.5" />
            AWS
          </span>
        </div>
      </div>
    </aside>
  );
}
