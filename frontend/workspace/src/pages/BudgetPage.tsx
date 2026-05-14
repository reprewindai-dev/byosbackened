import { useState } from "react";
import { AlertTriangle, DollarSign, PlusCircle, Trash2, TrendingUp } from "lucide-react";
import { useBudgetAlerts, useBudgetCaps, useCreateBudgetCap, useDeleteBudgetCap } from "@/hooks/useBudget";
import { cn } from "@/lib/cn";

export function BudgetPage() {
  const capsQ = useBudgetCaps();
  const alertsQ = useBudgetAlerts();
  const createCap = useCreateBudgetCap();
  const deleteCap = useDeleteBudgetCap();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ scope: "workspace" as const, scope_id: "self", scope_label: "Workspace", period: "monthly" as const, limit_usd: 50, alert_threshold_pct: 80, hard_stop: false });

  const unresolved = (alertsQ.data ?? []).filter((a) => !a.resolved);

  return (
    <div>
      <header className="mb-6 border-b border-rule pb-6">
        <div className="text-eyebrow">Cost Controls</div>
        <h1 className="mt-2 text-2xl font-semibold tracking-[-0.035em] text-bone">Budget Caps & Alerts</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
          Set hard or soft spending caps per workspace, model, or user. Get alerted before you hit limits.
        </p>
      </header>

      {/* Active Alerts */}
      {unresolved.length > 0 && (
        <section className="mb-6 space-y-2">
          <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold text-crimson">
            <AlertTriangle className="h-4 w-4" /> {unresolved.length} Active Budget Alert{unresolved.length > 1 ? "s" : ""}
          </h2>
          {unresolved.map((alert) => (
            <div key={alert.id} className="frame flex items-center justify-between gap-4 border-crimson/30 bg-crimson/5 p-4">
              <div>
                <div className="text-sm font-semibold text-bone">{alert.scope_label}</div>
                <div className="mt-0.5 text-xs text-muted">
                  ${alert.spent_usd.toFixed(2)} of ${alert.limit_usd.toFixed(2)} — {alert.threshold_pct}% threshold breached
                </div>
              </div>
              <span className="v-chip v-chip-err">over threshold</span>
            </div>
          ))}
        </section>
      )}

      {/* Budget Caps */}
      <section className="mb-6">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-bone">
            <DollarSign className="h-4 w-4 text-brass" /> Budget Caps
          </h2>
          <button type="button" onClick={() => setShowForm((v) => !v)} className="flex items-center gap-1.5 rounded-lg border border-rule px-3 py-1.5 text-xs text-bone hover:bg-white/[0.04]">
            <PlusCircle className="h-3.5 w-3.5" /> New cap
          </button>
        </div>

        {showForm && (
          <form
            className="frame mb-4 grid gap-4 p-4 md:grid-cols-3"
            onSubmit={async (e) => {
              e.preventDefault();
              await createCap.mutateAsync(form);
              setShowForm(false);
            }}
          >
            <label className="col-span-3 space-y-1 md:col-span-1">
              <span className="text-xs text-muted">Scope label</span>
              <input value={form.scope_label} onChange={(e) => setForm((f) => ({ ...f, scope_label: e.target.value }))} className="v-input w-full" />
            </label>
            <label className="space-y-1">
              <span className="text-xs text-muted">Period</span>
              <select value={form.period} onChange={(e) => setForm((f) => ({ ...f, period: e.target.value as typeof form.period }))} className="v-input w-full">
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
            </label>
            <label className="space-y-1">
              <span className="text-xs text-muted">Limit (USD)</span>
              <input type="number" min={1} value={form.limit_usd} onChange={(e) => setForm((f) => ({ ...f, limit_usd: Number(e.target.value) }))} className="v-input w-full" />
            </label>
            <label className="space-y-1">
              <span className="text-xs text-muted">Alert at (%)</span>
              <input type="number" min={10} max={100} value={form.alert_threshold_pct} onChange={(e) => setForm((f) => ({ ...f, alert_threshold_pct: Number(e.target.value) }))} className="v-input w-full" />
            </label>
            <label className="flex items-center gap-2 text-sm text-bone-2">
              <input type="checkbox" checked={form.hard_stop} onChange={(e) => setForm((f) => ({ ...f, hard_stop: e.target.checked }))} />
              Hard stop (block when exceeded)
            </label>
            <div className="col-span-3 flex gap-3">
              <button type="submit" disabled={createCap.isPending} className="v-btn-primary text-sm">{createCap.isPending ? "Saving…" : "Create cap"}</button>
              <button type="button" onClick={() => setShowForm(false)} className="v-btn text-sm">Cancel</button>
            </div>
          </form>
        )}

        {capsQ.isLoading ? (
          <div className="space-y-2">{Array.from({ length: 3 }).map((_, i) => <div key={i} className="frame h-16 animate-pulse bg-white/[0.02]" />)}</div>
        ) : capsQ.isError ? (
          <div className="frame border-crimson/30 bg-crimson/5 p-4 text-sm text-crimson">Could not load budget caps — /budget/caps may not be deployed yet.</div>
        ) : (capsQ.data ?? []).length === 0 ? (
          <div className="frame border-dashed p-8 text-center text-sm text-muted">No budget caps configured. Create one to start tracking spend limits.</div>
        ) : (
          <div className="space-y-2">
            {(capsQ.data ?? []).map((cap) => (
              <div key={cap.id} className="frame p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-semibold text-bone">{cap.scope_label}</div>
                    <div className="mt-0.5 text-xs text-muted capitalize">{cap.scope} · {cap.period} · resets {new Date(cap.resets_at).toLocaleDateString()}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusChip status={cap.status} />
                    <button type="button" onClick={() => deleteCap.mutate(cap.id)} aria-label="Delete cap" className="text-muted hover:text-crimson">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
                <div className="mt-3">
                  <div className="mb-1 flex justify-between text-xs text-muted">
                    <span>${cap.spent_usd.toFixed(2)} spent</span>
                    <span>${cap.limit_usd.toFixed(2)} limit</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-white/[0.06]">
                    <div
                      className={cn("h-full rounded-full transition-all", cap.utilization_pct >= 100 ? "bg-crimson" : cap.utilization_pct >= cap.alert_threshold_pct ? "bg-brass" : "bg-moss")}
                      style={{ width: `${Math.min(cap.utilization_pct, 100)}%` }}
                    />
                  </div>
                  <div className="mt-1 text-right text-xs text-muted">{cap.utilization_pct.toFixed(1)}% used{cap.hard_stop ? " · hard stop" : ""}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Alert History */}
      <section>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-bone">
          <TrendingUp className="h-4 w-4 text-brass" /> Alert History
        </h2>
        {alertsQ.isLoading ? (
          <div className="frame h-16 animate-pulse bg-white/[0.02]" />
        ) : (alertsQ.data ?? []).length === 0 ? (
          <div className="frame border-dashed p-6 text-center text-sm text-muted">No alerts triggered yet.</div>
        ) : (
          <div className="frame overflow-hidden">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-rule bg-white/[0.02] text-eyebrow">
                <tr>{["Scope", "Threshold", "Spent", "Limit", "Triggered", "Resolved"].map((h) => <th key={h} className="px-4 py-3">{h}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-rule">
                {(alertsQ.data ?? []).map((a) => (
                  <tr key={a.id} className="hover:bg-white/[0.02]">
                    <td className="px-4 py-3 text-bone">{a.scope_label}</td>
                    <td className="px-4 py-3 text-bone-2">{a.threshold_pct}%</td>
                    <td className="px-4 py-3 font-mono text-bone-2">${a.spent_usd.toFixed(2)}</td>
                    <td className="px-4 py-3 font-mono text-bone-2">${a.limit_usd.toFixed(2)}</td>
                    <td className="px-4 py-3 text-muted">{new Date(a.triggered_at).toLocaleString()}</td>
                    <td className="px-4 py-3">{a.resolved ? <span className="v-chip v-chip-ok">resolved</span> : <span className="v-chip v-chip-err">open</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function StatusChip({ status }: { status: string }) {
  return (
    <span className={cn("v-chip",
      status === "ok" && "v-chip-ok",
      status === "warning" && "v-chip-warn",
      status === "exceeded" && "v-chip-err",
      status === "paused" && "v-chip-brass",
    )}>{status}</span>
  );
}
