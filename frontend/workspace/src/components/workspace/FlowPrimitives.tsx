import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Activity, AlertCircle, ArrowRight, CheckCircle2, Clock3, ShieldCheck, XCircle } from "lucide-react";
import { cn } from "@/lib/cn";
import { actionUnavailableMessage } from "@/lib/errors";

export type FlowStatus = "idle" | "running" | "succeeded" | "failed" | "blocked" | "unavailable";

export interface FlowStep {
  label: string;
  status: FlowStatus;
  detail?: string;
}

export interface FlowMetric {
  label: string;
  value: string;
}

export interface FlowAction {
  label: string;
  to?: string;
  href?: string;
  onClick?: () => void;
  disabled?: boolean;
  primary?: boolean;
}

export function RunStatePanel({
  eyebrow = "Run state",
  title,
  status,
  summary,
  steps = [],
  metrics = [],
  result,
  error,
  actions = [],
  className,
}: {
  eyebrow?: string;
  title: string;
  status: FlowStatus;
  summary?: string;
  steps?: FlowStep[];
  metrics?: FlowMetric[];
  result?: ReactNode;
  error?: unknown;
  actions?: FlowAction[];
  className?: string;
}) {
  return (
    <section className={cn("frame overflow-hidden", className)}>
      <header className="flex flex-wrap items-start justify-between gap-3 border-b border-rule/80 bg-ink-1/60 px-4 py-3">
        <div>
          <div className="text-eyebrow">{eyebrow}</div>
          <h3 className="font-display mt-1 text-sm font-semibold text-bone">{title}</h3>
          {summary && <p className="mt-1 text-[12px] leading-relaxed text-muted">{summary}</p>}
        </div>
        <FlowBadge status={status} />
      </header>

      <div className="space-y-3 p-4">
        {steps.length > 0 && (
          <div className="grid gap-2">
            {steps.map((step, index) => (
              <div key={`${step.label}-${index}`} className="grid grid-cols-[28px_1fr_auto] items-center gap-3 rounded-md border border-rule/70 bg-ink-2/65 px-3 py-2">
                <span className={cn("grid h-7 w-7 place-items-center rounded-md border font-mono text-[11px]", stepTone(step.status))}>
                  {index + 1}
                </span>
                <div className="min-w-0">
                  <div className="truncate text-sm text-bone">{step.label}</div>
                  {step.detail && <div className="truncate font-mono text-[10px] uppercase tracking-[0.12em] text-muted">{step.detail}</div>}
                </div>
                <FlowBadge status={step.status} compact />
              </div>
            ))}
          </div>
        )}

        {metrics.length > 0 && (
          <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
            {metrics.map((metric) => (
              <div key={metric.label} className="rounded-md border border-rule/60 bg-black/10 px-3 py-2">
                <div className="text-[10px] uppercase tracking-[0.18em] text-muted">{metric.label}</div>
                <div className="mt-1 truncate text-sm font-semibold text-bone">{metric.value}</div>
              </div>
            ))}
          </div>
        )}

        {Boolean(error) && <LiveErrorBox title={`${title} failed`} error={error} />}

        {result && (
          <div className="rounded-lg border border-rule/70 bg-black/20 p-3">
            {result}
          </div>
        )}

        {actions.length > 0 && <NextActionRail actions={actions} />}
      </div>
    </section>
  );
}

export function ProofStrip({ items, className }: { items: FlowMetric[]; className?: string }) {
  return (
    <div className={cn("grid gap-2 md:grid-cols-4", className)}>
      {items.map((item) => (
        <div key={item.label} className="rounded-md border border-moss/20 bg-moss/[0.035] px-3 py-2">
          <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-[0.16em] text-moss">
            <ShieldCheck className="h-3 w-3" />
            {item.label}
          </div>
          <div className="mt-1 truncate font-mono text-[12px] text-bone">{item.value}</div>
        </div>
      ))}
    </div>
  );
}

export function NextActionRail({ actions }: { actions: FlowAction[] }) {
  return (
    <div className="flex flex-wrap gap-2 border-t border-rule/80 pt-3">
      {actions.map((action) => (
        <FlowActionButton key={action.label} action={action} />
      ))}
    </div>
  );
}

export function LiveErrorBox({ title, error }: { title: string; error: unknown }) {
  return (
    <div className="flex items-start gap-3 rounded-md border border-crimson/35 bg-crimson/5 p-3 text-[12px] text-crimson">
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
      <div>
        <div className="font-semibold">{title}</div>
        <div className="mt-1 opacity-85">{actionUnavailableMessage(error, title)}</div>
      </div>
    </div>
  );
}

export function ResultDrawer({
  open,
  title,
  eyebrow = "Result",
  onClose,
  children,
}: {
  open: boolean;
  title: string;
  eyebrow?: string;
  onClose: () => void;
  children: ReactNode;
}) {
  if (!open) return null;
  return (
    <aside className="fixed right-4 top-24 z-50 w-[min(520px,calc(100vw-2rem))] overflow-hidden rounded-xl border border-brass/25 bg-ink/95 shadow-2xl shadow-black/50 backdrop-blur-xl">
      <header className="flex items-start justify-between gap-3 border-b border-rule/80 bg-brass/[0.055] px-4 py-3">
        <div>
          <div className="text-eyebrow">{eyebrow}</div>
          <h3 className="font-display mt-1 text-base font-semibold text-bone">{title}</h3>
        </div>
        <button type="button" className="text-muted transition hover:text-bone" onClick={onClose} aria-label="Close result drawer">
          <XCircle className="h-4 w-4" />
        </button>
      </header>
      <div className="max-h-[calc(100vh-9rem)] overflow-auto p-4">{children}</div>
    </aside>
  );
}

function FlowActionButton({ action }: { action: FlowAction }) {
  const className = cn(action.primary ? "v-btn-primary" : "v-btn-ghost", "h-8 px-3 text-xs");
  const content = (
    <>
      {action.label}
      <ArrowRight className="h-3.5 w-3.5" />
    </>
  );

  if (action.disabled) {
    return (
      <button type="button" className={className} disabled>
        {content}
      </button>
    );
  }

  if (action.to) {
    return (
      <Link className={className} to={action.to}>
        {content}
      </Link>
    );
  }
  if (action.href) {
    return (
      <a className={className} href={action.href}>
        {content}
      </a>
    );
  }
  return (
    <button type="button" className={className} disabled={action.disabled} onClick={action.onClick}>
      {content}
    </button>
  );
}

function FlowBadge({ status, compact }: { status: FlowStatus; compact?: boolean }) {
  const icon =
    status === "running" ? <Activity className="h-3 w-3 animate-spin" /> :
    status === "succeeded" ? <CheckCircle2 className="h-3 w-3" /> :
    status === "failed" || status === "blocked" ? <AlertCircle className="h-3 w-3" /> :
    <Clock3 className="h-3 w-3" />;
  return (
    <span className={cn("chip", badgeTone(status), compact && "px-1.5 py-0.5 text-[10px]")}>
      {icon}
      {status}
    </span>
  );
}

function badgeTone(status: FlowStatus): string {
  if (status === "running") return "border-brass/40 bg-brass/5 text-brass-2";
  if (status === "succeeded") return "border-moss/30 bg-moss/5 text-moss";
  if (status === "failed" || status === "blocked") return "border-crimson/30 bg-crimson/5 text-crimson";
  if (status === "unavailable") return "border-amber/30 bg-amber/5 text-amber";
  return "border-rule bg-white/[0.02] text-bone-2";
}

function stepTone(status: FlowStatus): string {
  if (status === "running") return "border-brass/40 bg-brass/10 text-brass-2";
  if (status === "succeeded") return "border-moss/35 bg-moss/10 text-moss";
  if (status === "failed" || status === "blocked") return "border-crimson/35 bg-crimson/10 text-crimson";
  if (status === "unavailable") return "border-amber/35 bg-amber/10 text-amber";
  return "border-rule bg-white/[0.03] text-muted";
}
