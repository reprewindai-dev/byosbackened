import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  ArrowUpRight,
  Box,
  CheckCircle2,
  Cloud,
  Plus,
  RotateCcw,
  Server,
  ShieldCheck,
  X,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn, fmtNumber, relativeTime } from "@/lib/cn";
import { actionUnavailableMessage, isRouteUnavailable } from "@/lib/errors";

interface Deployment {
  id: string;
  name?: string | null;
  slug?: string | null;
  region: string;
  service_type: string;
  model_slug?: string | null;
  provider?: string | null;
  version?: string | null;
  previous_version?: string | null;
  strategy: "direct" | "blue_green" | "canary";
  status: "active" | "inactive" | "failed" | "promoting" | "rolling_back";
  traffic_percent: number;
  is_primary: boolean;
  health_metrics: Record<string, number>;
  deployed_at?: string | null;
  promoted_at?: string | null;
  rolled_back_at?: string | null;
  last_health_check?: string | null;
}

interface DeploymentsResp {
  total: number;
  items: Deployment[];
  zones: Array<{ region: string; deployments: Deployment[]; active_count: number }>;
}

async function fetchDeployments(): Promise<DeploymentsResp> {
  const r = await api.get<DeploymentsResp>("/deployments");
  return r.data;
}

export function DeploymentsPage() {
  const qc = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["deployments"],
    queryFn: fetchDeployments,
    refetchInterval: 20_000,
  });

  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState({
    name: "",
    region: "hetzner-fsn1",
    model_slug: "qwen2.5:3b",
    provider: "ollama",
    version: "v1",
    strategy: "direct" as "direct" | "blue_green" | "canary",
    traffic_percent: 100,
  });

  const createMut = useMutation({
    mutationFn: async (payload: typeof form) => {
      const r = await api.post<Deployment>("/deployments", payload);
      return r.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["deployments"] });
      setShowNew(false);
      setForm({ ...form, name: "" });
    },
  });

  const promoteMut = useMutation({
    mutationFn: async (id: string) => {
      const r = await api.post(`/deployments/${id}/promote`, { target_traffic_percent: 100 });
      return r.data;
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ["deployments"] }),
  });

  const rollbackMut = useMutation({
    mutationFn: async (id: string) => {
      const r = await api.post(`/deployments/${id}/rollback`, {});
      return r.data;
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ["deployments"] }),
  });

  const total = data?.total ?? 0;
  const active = data?.items.filter((d) => d.status === "active").length ?? 0;
  const zones = data?.zones ?? [];
  const deploymentsUnavailable = isRouteUnavailable(error) || isRouteUnavailable(createMut.error);

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-1 font-mono text-[11px] uppercase tracking-[0.15em] text-muted">
            Workspace · Deployments
          </div>
          <h1 className="text-3xl font-semibold tracking-tight">Fleet, traffic &amp; rollouts</h1>
          <p className="mt-2 max-w-2xl text-sm text-bone-2">
            Model deployments grouped by zone. Blue/green and canary strategies with one-click promote
            and rollback. Each transition writes to the audit ledger.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <span className="v-chip v-chip-ok">
              <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-moss" />
              live · <span className="font-mono">/api/v1/deployments</span>
            </span>
            <span className="v-chip v-chip-brass">{active} / {total} active</span>
          </div>
        </div>
        <button className="v-btn-primary" disabled={deploymentsUnavailable} onClick={() => setShowNew(true)}>
          <Plus className="h-4 w-4" /> New deployment
        </button>
      </header>

      {deploymentsUnavailable && (
        <div className="v-card border-brass/40 bg-brass/5 p-4 text-sm text-brass-2">
          Deployment creation is not enabled on the live backend yet. Existing deployments and health status remain readable.
        </div>
      )}

      <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Kpi icon={<Box className="h-3 w-3" />} label="Deployments" value={fmtNumber(total)} />
        <Kpi icon={<CheckCircle2 className="h-3 w-3" />} label="Active" value={fmtNumber(active)} />
        <Kpi icon={<Server className="h-3 w-3" />} label="Zones" value={String(zones.length)} />
        <Kpi icon={<ShieldCheck className="h-3 w-3" />} label="mTLS" value="enforced" />
      </section>

      {isLoading && (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {Array.from({ length: 2 }).map((_, i) => (
            <div key={i} className="v-card h-40 animate-pulse bg-ink-2" />
          ))}
        </div>
      )}

      {!isLoading && zones.length === 0 && (
        <div className="v-card flex flex-col items-center gap-3 px-6 py-16 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brass/10 text-brass-2">
            <Cloud className="h-6 w-6" />
          </div>
          <div className="text-lg font-semibold">No deployments yet</div>
          <p className="max-w-md text-sm text-bone-2">
            Spin up your first deployment to register a model in a zone with a chosen rollout strategy.
          </p>
          <button className="v-btn-primary" disabled={deploymentsUnavailable} onClick={() => setShowNew(true)}>
            <Plus className="h-4 w-4" /> New deployment
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {zones.map((zone) => (
          <section key={zone.region} className="v-card p-0">
            <header className="flex items-center justify-between border-b border-rule px-5 py-3">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-md bg-brass/10 text-brass-2">
                  <Server className="h-4 w-4" />
                </div>
                <div>
                  <div className="text-[15px] font-semibold text-bone">{zone.region}</div>
                  <div className="font-mono text-[11px] text-muted">
                    {zone.active_count} / {zone.deployments.length} active
                  </div>
                </div>
              </div>
              <span className={cn(
                "v-chip font-mono text-[10px]",
                zone.active_count > 0 ? "v-chip-ok" : "v-chip-warn",
              )}>
                <Activity className="h-3 w-3" />
                {zone.active_count > 0 ? "healthy" : "idle"}
              </span>
            </header>
            <ul className="divide-y divide-rule/50">
              {zone.deployments.map((d) => (
                <li key={d.id} className="px-5 py-3">
                  <div className="flex items-start gap-3">
                    <div className={cn(
                      "mt-1 h-1.5 w-1.5 shrink-0 rounded-full",
                      d.status === "active" ? "bg-moss"
                        : d.status === "failed" ? "bg-crimson"
                        : d.status === "promoting" || d.status === "rolling_back" ? "bg-brass"
                        : "bg-rule",
                    )} />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-[13px] font-semibold text-bone">{d.name ?? d.slug ?? d.id}</span>
                        <span className="v-chip font-mono text-[10px]">{d.strategy}</span>
                        <span className="v-chip font-mono text-[10px]">{d.status}</span>
                        {d.is_primary && <span className="v-chip v-chip-ok font-mono text-[10px]">primary</span>}
                      </div>
                      <div className="mt-1 truncate font-mono text-[11px] text-muted">
                        {d.model_slug ?? "—"}
                        {d.version ? ` · ${d.version}` : ""}
                        {d.previous_version ? ` (← ${d.previous_version})` : ""}
                        {" · "}
                        {d.traffic_percent}% traffic
                        {d.deployed_at && ` · deployed ${relativeTime(d.deployed_at)}`}
                      </div>
                    </div>
                    <div className="flex shrink-0 gap-1">
                      {d.status !== "active" || d.traffic_percent < 100 ? (
                        <button
                          className="v-btn-ghost"
                          disabled={promoteMut.isPending}
                          onClick={() => promoteMut.mutate(d.id)}
                          title="Promote to 100%"
                        >
                          <ArrowUpRight className="h-3.5 w-3.5" />
                        </button>
                      ) : null}
                      {d.is_primary && d.previous_version ? (
                        <button
                          className="v-btn-ghost"
                          disabled={rollbackMut.isPending}
                          onClick={() => rollbackMut.mutate(d.id)}
                          title="Rollback"
                        >
                          <RotateCcw className="h-3.5 w-3.5" />
                        </button>
                      ) : null}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>

      {/* New deployment modal */}
      {showNew && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/80 backdrop-blur-sm">
          <div className="v-card w-full max-w-md p-5">
            <header className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold">New deployment</h3>
              <button className="text-muted hover:text-bone" onClick={() => setShowNew(false)}>
                <X className="h-4 w-4" />
              </button>
            </header>
            <div className="space-y-3">
              <Field label="Name">
                <input className="v-input w-full" value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="qwen-prod-fsn1" autoFocus />
              </Field>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Region">
                  <input className="v-input w-full" value={form.region}
                    onChange={(e) => setForm({ ...form, region: e.target.value })} />
                </Field>
                <Field label="Provider">
                  <select className="v-input w-full" value={form.provider}
                    onChange={(e) => setForm({ ...form, provider: e.target.value })}>
                    <option value="ollama">ollama</option>
                    <option value="groq">groq</option>
                    <option value="hetzner">hetzner</option>
                    <option value="aws">aws</option>
                  </select>
                </Field>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Model slug">
                  <input className="v-input w-full" value={form.model_slug}
                    onChange={(e) => setForm({ ...form, model_slug: e.target.value })} />
                </Field>
                <Field label="Version">
                  <input className="v-input w-full" value={form.version}
                    onChange={(e) => setForm({ ...form, version: e.target.value })} />
                </Field>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Strategy">
                  <select className="v-input w-full" value={form.strategy}
                    onChange={(e) => setForm({ ...form, strategy: e.target.value as typeof form.strategy })}>
                    <option value="direct">direct</option>
                    <option value="blue_green">blue/green</option>
                    <option value="canary">canary</option>
                  </select>
                </Field>
                <Field label="Initial traffic %">
                  <input type="number" min={0} max={100} className="v-input w-full"
                    value={form.traffic_percent}
                    onChange={(e) => setForm({ ...form, traffic_percent: Math.max(0, Math.min(100, +e.target.value)) })} />
                </Field>
              </div>
              {createMut.isError && (
                <div className="text-[12px] text-crimson">
                  {actionUnavailableMessage(createMut.error, "Deployment creation")}
                </div>
              )}
              <div className="flex justify-end gap-2">
                <button className="v-btn-ghost" onClick={() => setShowNew(false)}>Cancel</button>
                <button className="v-btn-primary"
                  disabled={!form.name || createMut.isPending}
                  onClick={() => createMut.mutate(form)}>
                  {createMut.isPending ? "Creating…" : "Create"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Kpi({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="v-card p-4">
      <div className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.1em] text-muted">
        {icon}{label}
      </div>
      <div className="mt-1.5 text-xl font-semibold text-bone">{value}</div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <div className="mb-1 font-mono text-[10px] uppercase tracking-wider text-muted">{label}</div>
      {children}
    </label>
  );
}
