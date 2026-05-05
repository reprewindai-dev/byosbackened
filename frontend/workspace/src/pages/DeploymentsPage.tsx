import { useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertCircle,
  ArrowUpRight,
  Copy,
  KeyRound,
  MoreHorizontal,
  Plus,
  RotateCcw,
  Server,
  Webhook,
  X,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn, relativeTime } from "@/lib/cn";
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
  health_metrics: Record<string, unknown>;
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
  const [showNew, setShowNew] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: "",
    region: "hetzner-fsn1",
    service_type: "api",
    model_slug: "qwen2.5:3b",
    provider: "ollama",
    version: "v1",
    strategy: "direct" as "direct" | "blue_green" | "canary",
    traffic_percent: 100,
  });

  const { data, isLoading, error } = useQuery({
    queryKey: ["deployments"],
    queryFn: fetchDeployments,
    refetchInterval: 20_000,
  });

  const createMut = useMutation({
    mutationFn: async (payload: typeof form) => {
      const r = await api.post<Deployment>("/deployments", payload);
      return r.data;
    },
    onSuccess: (created) => {
      qc.invalidateQueries({ queryKey: ["deployments"] });
      setSelectedId(created.id);
      setShowNew(false);
      setForm((current) => ({ ...current, name: "" }));
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

  const deployments = data?.items ?? [];
  const selected = deployments.find((deployment) => deployment.id === selectedId) ?? deployments[0] ?? null;
  const deploymentsUnavailable = isRouteUnavailable(error) || isRouteUnavailable(createMut.error);

  return (
    <div className="mx-auto w-full max-w-[1400px]">
      <PageHeader onNew={() => setShowNew(true)} routeUnavailable={deploymentsUnavailable} count={deployments.length} />

      {deploymentsUnavailable && (
        <div className="frame mb-4 flex items-start gap-3 border-brass/40 bg-brass/5 p-4 text-sm text-brass-2">
          <AlertCircle className="mt-0.5 h-4 w-4" />
          <div>
            Deployment creation is not enabled on the live backend yet. Existing deployments and health status remain
            readable.
          </div>
        </div>
      )}

      <section>
        <EndpointTable
          deployments={deployments}
          loading={isLoading}
          selectedId={selected?.id ?? null}
          onSelect={setSelectedId}
          onNew={() => setShowNew(true)}
          routeUnavailable={deploymentsUnavailable}
        />

        <div className="mt-4 grid grid-cols-12 gap-4">
          <EndpointDetail
            deployment={selected}
            promotePending={promoteMut.isPending}
            rollbackPending={rollbackMut.isPending}
            onPromote={(id) => promoteMut.mutate(id)}
            onRollback={(id) => rollbackMut.mutate(id)}
          />
          <DropInPanel />
        </div>
      </section>

      {showNew && (
        <NewDeploymentModal
          form={form}
          setForm={setForm}
          pending={createMut.isPending}
          error={createMut.error}
          onClose={() => setShowNew(false)}
          onCreate={() => createMut.mutate(form)}
        />
      )}
    </div>
  );
}

function PageHeader({ onNew, routeUnavailable, count }: { onNew: () => void; routeUnavailable: boolean; count: number }) {
  return (
    <header className="mb-5 flex flex-wrap items-start justify-between gap-4">
      <div>
        <div className="text-eyebrow">Deployments · endpoints</div>
        <h1 className="font-display mt-1 text-[30px] font-semibold tracking-tight text-bone">
          OpenAI-compatible endpoints
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-bone-2">
          Chat, completion, embedding, pipeline, and async batch endpoints - each with auth, rate limits, CORS,
          webhooks, and SDK guides.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Badge tone="ok" dot>
            live · <span className="font-mono">/api/v1/deployments</span>
          </Badge>
          <Badge tone="primary">{count} endpoints</Badge>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        <button
          className="v-btn-ghost h-8 cursor-not-allowed px-3 text-xs opacity-70"
          disabled
          title="Webhook management is not exposed on this backend route yet."
        >
          <Webhook className="h-3.5 w-3.5" /> Webhooks
        </button>
        <button className="v-btn-primary h-8 px-3 text-xs" disabled={routeUnavailable} onClick={onNew}>
          <Plus className="h-3.5 w-3.5" /> New endpoint
        </button>
      </div>
    </header>
  );
}

function EndpointTable({
  deployments,
  loading,
  selectedId,
  onSelect,
  onNew,
  routeUnavailable,
}: {
  deployments: Deployment[];
  loading: boolean;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  routeUnavailable: boolean;
}) {
  return (
    <div className="frame overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[960px] text-[12.5px]">
          <thead className="border-b border-rule/70 bg-ink-1/70 text-eyebrow">
            <tr>
              <th className="px-4 py-2 text-left">Endpoint</th>
              <th className="px-4 py-2 text-left">Type</th>
              <th className="px-4 py-2 text-left">Model</th>
              <th className="px-4 py-2 text-left">Region</th>
              <th className="px-4 py-2 text-left">Auth</th>
              <th className="px-4 py-2 text-left">Rate limit</th>
              <th className="px-4 py-2 text-right">RPS</th>
              <th className="px-4 py-2 text-right">Errors</th>
              <th className="px-4 py-2 text-left">Status</th>
              <th className="px-4 py-2 text-right" />
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={10} className="px-5 py-8 text-center font-mono text-[12px] text-muted">
                  loading...
                </td>
              </tr>
            )}
            {!loading && deployments.length === 0 && (
              <tr>
                <td colSpan={10} className="px-5 py-12 text-center">
                  <div className="flex flex-col items-center gap-3">
                    <Server className="h-8 w-8 text-brass-2" />
                    <div className="text-sm text-bone-2">No endpoints yet. Create one from a governed deployment.</div>
                    <button className="v-btn-primary" disabled={routeUnavailable} onClick={onNew}>
                      <Plus className="h-4 w-4" /> New endpoint
                    </button>
                  </div>
                </td>
              </tr>
            )}
            {deployments.map((deployment) => {
              const metrics = deployment.health_metrics ?? {};
              const rps = metricNumber(metrics, ["rps", "requests_per_second"]);
              const errorRate = metricNumber(metrics, ["error_rate", "errors_pct"]);
              return (
                <tr
                  key={deployment.id}
                  className={cn(
                    "border-b border-rule/50 last:border-0 hover-elevate",
                    selectedId === deployment.id && "bg-brass/5",
                  )}
                >
                  <td className="px-4 py-2 align-top">
                    <button className="block text-left font-mono text-bone hover:text-brass-2" onClick={() => onSelect(deployment.id)}>
                      {deployment.name ?? deployment.slug ?? deployment.id}
                    </button>
                    <div className="max-w-[260px] truncate text-[11px] text-muted">{endpointPath(deployment)}</div>
                  </td>
                  <td className="px-4 py-2">
                    <Badge tone="muted">{deployment.service_type || "api"}</Badge>
                  </td>
                  <td className="px-4 py-2 font-mono text-[11.5px] text-muted">{deployment.model_slug ?? "not set"}</td>
                  <td className="px-4 py-2 font-mono text-bone-2">{deployment.region}</td>
                  <td className="px-4 py-2">
                    <Badge tone="info">
                      <KeyRound className="h-3 w-3" /> Bearer
                    </Badge>
                  </td>
                  <td className="px-4 py-2 text-muted">{metricString(metrics, ["rate_limit", "rpm"]) ?? "not reported"}</td>
                  <td className="px-4 py-2 text-right font-mono">{rps === undefined ? "no data" : rps.toFixed(1)}</td>
                  <td className="px-4 py-2 text-right font-mono">
                    {errorRate === undefined ? "no data" : `${(errorRate * 100).toFixed(2)}%`}
                  </td>
                  <td className="px-4 py-2">
                    <StatusBadge status={deployment.status} />
                  </td>
                  <td className="px-4 py-2 text-right">
                    <button className="v-btn-ghost h-7 px-2" onClick={() => onSelect(deployment.id)}>
                      <MoreHorizontal className="h-3.5 w-3.5" />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function EndpointDetail({
  deployment,
  promotePending,
  rollbackPending,
  onPromote,
  onRollback,
}: {
  deployment: Deployment | null;
  promotePending: boolean;
  rollbackPending: boolean;
  onPromote: (id: string) => void;
  onRollback: (id: string) => void;
}) {
  if (!deployment) {
    return (
      <div className="frame col-span-12 p-4 lg:col-span-7">
        <div className="text-eyebrow">Endpoint detail</div>
        <div className="mt-8 text-center text-sm text-muted">No deployment selected yet.</div>
      </div>
    );
  }

  const metrics = deployment.health_metrics ?? {};
  const rpsSeries = toNumberArray(metrics.rps_series);
  const p50 = metricNumber(metrics, ["p50_ms", "latency_p50_ms"]);

  return (
    <div className="frame col-span-12 p-4 lg:col-span-7">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="text-eyebrow">Endpoint detail · {deployment.name ?? deployment.slug ?? deployment.id}</div>
          <div className="font-display truncate text-[14px] font-semibold text-bone">{endpointPath(deployment)}</div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={deployment.status} />
          <Badge tone={deployment.provider === "ollama" ? "primary" : "info"}>{deployment.provider ?? "provider unset"}</Badge>
          <Badge tone="muted">{p50 === undefined ? "p50 no data" : `p50 ${p50}ms`}</Badge>
        </div>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 text-[11.5px] md:grid-cols-3">
        <DetailTile label="Auth" value="Bearer required" />
        <DetailTile label="Rate" value={metricString(metrics, ["rate_limit", "rpm"]) ?? "not reported"} />
        <DetailTile label="Timeout" value={metricString(metrics, ["timeout", "timeout_s"]) ?? "not reported"} />
        <DetailTile label="CORS" value={metricString(metrics, ["cors"]) ?? "not reported"} />
        <DetailTile label="IP allowlist" value={metricString(metrics, ["ip_allowlist"]) ?? "not reported"} />
        <DetailTile label="Webhook" value={metricString(metrics, ["webhook"]) ?? "not reported"} />
      </div>

      <div className="mt-4">
        <div className="mb-1.5 text-eyebrow">RPS · last 24h</div>
        <MiniSeries data={rpsSeries} empty="No RPS health series returned yet" />
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-rule/80 pt-3">
        <div className="font-mono text-[11px] text-muted">
          {deployment.model_slug ?? "model unset"}
          {deployment.version ? ` · ${deployment.version}` : ""}
          {deployment.deployed_at ? ` · deployed ${relativeTime(deployment.deployed_at)}` : ""}
        </div>
        <div className="flex gap-2">
          <button
            className="v-btn-ghost h-8 px-3 text-xs"
            disabled={promotePending || (deployment.status === "active" && deployment.traffic_percent === 100)}
            onClick={() => onPromote(deployment.id)}
          >
            <ArrowUpRight className="h-3.5 w-3.5" /> Promote
          </button>
          <button
            className="v-btn-ghost h-8 px-3 text-xs"
            disabled={rollbackPending || !deployment.previous_version}
            onClick={() => onRollback(deployment.id)}
          >
            <RotateCcw className="h-3.5 w-3.5" /> Rollback
          </button>
        </div>
      </div>
    </div>
  );
}

function DropInPanel() {
  const snippet = `from openai import OpenAI
client = OpenAI(
  base_url="https://api.veklom.com/v1",
  api_key=os.environ["VEKLOM_API_KEY"],
)
client.chat.completions.create(
  model="your-deployed-model",
  messages=[{"role": "user", "content": "hi"}],
)`;

  return (
    <div className="frame col-span-12 p-4 lg:col-span-5">
      <div className="text-eyebrow">Adoption · drop-in</div>
      <div className="font-display text-[14px] font-semibold text-bone">Veklom is OpenAI-compatible</div>
      <p className="mt-1 text-[12px] text-muted">Existing OpenAI clients can switch the base URL and keep the same call shape.</p>
      <pre className="mt-3 max-h-[260px] overflow-auto rounded-md border border-rule bg-ink-1/70 p-3 font-mono text-[11.5px] leading-relaxed text-bone-2">
        {snippet}
      </pre>
      <div className="mt-3 flex items-center gap-2">
        <button className="v-btn-ghost h-8 px-3 text-xs" onClick={() => navigator.clipboard?.writeText(snippet)}>
          <Copy className="h-3.5 w-3.5" /> Copy
        </button>
        <a href="#/vault" className="v-btn-primary h-8 px-3 text-xs">
          <KeyRound className="h-3.5 w-3.5" /> API keys
        </a>
        <a href="#/monitoring" className="v-btn-ghost ml-auto h-8 px-3 text-xs">
          <Activity className="h-3.5 w-3.5" />
        </a>
      </div>
    </div>
  );
}

function NewDeploymentModal({
  form,
  setForm,
  pending,
  error,
  onClose,
  onCreate,
}: {
  form: {
    name: string;
    region: string;
    service_type: string;
    model_slug: string;
    provider: string;
    version: string;
    strategy: "direct" | "blue_green" | "canary";
    traffic_percent: number;
  };
  setForm: (form: {
    name: string;
    region: string;
    service_type: string;
    model_slug: string;
    provider: string;
    version: string;
    strategy: "direct" | "blue_green" | "canary";
    traffic_percent: number;
  }) => void;
  pending: boolean;
  error: unknown;
  onClose: () => void;
  onCreate: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/80 backdrop-blur-sm">
      <div className="frame w-full max-w-md p-5">
        <header className="mb-4 flex items-center justify-between">
          <h3 className="font-display text-lg font-semibold text-bone">New endpoint</h3>
          <button className="text-muted hover:text-bone" onClick={onClose}>
            <X className="h-4 w-4" />
          </button>
        </header>
        <div className="space-y-3">
          <Field label="Name">
            <input
              className="v-input"
              value={form.name}
              onChange={(event) => setForm({ ...form, name: event.target.value })}
              placeholder="qwen-prod-fsn1"
              autoFocus
            />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Region">
              <input className="v-input" value={form.region} onChange={(event) => setForm({ ...form, region: event.target.value })} />
            </Field>
            <Field label="Type">
              <input
                className="v-input"
                value={form.service_type}
                onChange={(event) => setForm({ ...form, service_type: event.target.value })}
              />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Provider">
              <select className="v-input" value={form.provider} onChange={(event) => setForm({ ...form, provider: event.target.value })}>
                <option value="ollama">ollama</option>
                <option value="groq">groq</option>
                <option value="hetzner">hetzner</option>
                <option value="aws">aws</option>
              </select>
            </Field>
            <Field label="Version">
              <input className="v-input" value={form.version} onChange={(event) => setForm({ ...form, version: event.target.value })} />
            </Field>
          </div>
          <Field label="Model slug">
            <input
              className="v-input"
              value={form.model_slug}
              onChange={(event) => setForm({ ...form, model_slug: event.target.value })}
            />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Strategy">
              <select
                className="v-input"
                value={form.strategy}
                onChange={(event) => setForm({ ...form, strategy: event.target.value as typeof form.strategy })}
              >
                <option value="direct">direct</option>
                <option value="blue_green">blue/green</option>
                <option value="canary">canary</option>
              </select>
            </Field>
            <Field label="Initial traffic %">
              <input
                type="number"
                min={0}
                max={100}
                className="v-input"
                value={form.traffic_percent}
                onChange={(event) => setForm({ ...form, traffic_percent: Math.max(0, Math.min(100, +event.target.value)) })}
              />
            </Field>
          </div>
          {Boolean(error) && (
            <div className="text-[12px] text-crimson">{actionUnavailableMessage(error, "Deployment creation")}</div>
          )}
          <div className="flex justify-end gap-2">
            <button className="v-btn-ghost" onClick={onClose}>
              Cancel
            </button>
            <button className="v-btn-primary" disabled={!form.name || pending} onClick={onCreate}>
              {pending ? "Creating..." : "Create"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function endpointPath(deployment: Deployment): string {
  const type = deployment.service_type || "api";
  const slug = deployment.slug || deployment.name || deployment.id;
  return `https://api.veklom.com/v1/${type}/${slug}`;
}

function metricNumber(metrics: Record<string, unknown>, keys: string[]): number | undefined {
  for (const key of keys) {
    const value = metrics[key];
    const numberValue = Number(value);
    if (Number.isFinite(numberValue)) return numberValue;
  }
  return undefined;
}

function metricString(metrics: Record<string, unknown>, keys: string[]): string | undefined {
  for (const key of keys) {
    const value = metrics[key];
    if (typeof value === "string" && value.trim()) return value;
    if (typeof value === "number" && Number.isFinite(value)) return String(value);
    if (typeof value === "boolean") return value ? "on" : "off";
  }
  return undefined;
}

function toNumberArray(value: unknown): number[] {
  if (!Array.isArray(value)) return [];
  return value.map(Number).filter((entry) => Number.isFinite(entry) && entry >= 0);
}

function MiniSeries({ data, empty }: { data: number[]; empty: string }) {
  if (!data.length) {
    return (
      <div className="grid h-16 place-items-center rounded-md border border-dashed border-rule bg-ink-1/50 font-mono text-[10px] uppercase tracking-[0.12em] text-muted">
        {empty}
      </div>
    );
  }
  const max = Math.max(1, ...data);
  const path = data
    .slice(-32)
    .map((value, index, rows) => {
      const x = rows.length === 1 ? 200 : (index / (rows.length - 1)) * 400;
      const y = 64 - (value / max) * 56;
      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
  return (
    <svg viewBox="0 0 400 70" className="h-16 w-full rounded-md border border-rule bg-ink-1/50" preserveAspectRatio="none">
      <path d={path} fill="none" stroke="rgba(229,177,110,0.95)" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function DetailTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-rule bg-ink-1/50 px-2.5 py-1.5">
      <div className="text-eyebrow">{label}</div>
      <div className="truncate font-mono text-bone">{value}</div>
    </div>
  );
}

function StatusBadge({ status }: { status: Deployment["status"] }) {
  if (status === "active") {
    return (
      <Badge tone="ok" dot>
        live
      </Badge>
    );
  }
  if (status === "failed") {
    return (
      <Badge tone="warn" dot>
        failed
      </Badge>
    );
  }
  if (status === "promoting" || status === "rolling_back") {
    return (
      <Badge tone="primary" dot>
        {status}
      </Badge>
    );
  }
  return (
    <Badge tone="muted" dot>
      {status}
    </Badge>
  );
}

function Badge({
  children,
  tone = "muted",
  dot,
}: {
  children: ReactNode;
  tone?: "muted" | "primary" | "ok" | "warn" | "info";
  dot?: boolean;
}) {
  return (
    <span
      className={cn(
        "chip",
        tone === "muted" && "border-rule bg-white/[0.02] text-bone-2",
        tone === "primary" && "border-brass/40 bg-brass/5 text-brass-2",
        tone === "ok" && "border-moss/30 bg-moss/5 text-moss",
        tone === "warn" && "border-amber/30 bg-amber/5 text-amber",
        tone === "info" && "border-electric/30 bg-electric/5 text-electric",
      )}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <div className="v-label">{label}</div>
      {children}
    </label>
  );
}
