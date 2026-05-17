import { useMemo, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  Box,
  Building2,
  CheckCircle2,
  ExternalLink,
  KeyRound,
  Loader2,
  Settings as Cog,
  Shield,
  ShieldAlert,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuthStore } from "@/store/auth-store";
import { cn, relativeTime } from "@/lib/cn";

type Tab = "identity" | "keys" | "models";

interface ApiKey {
  id: string;
  name: string;
  key_prefix?: string;
  created_at: string;
  last_used_at?: string | null;
  expires_at?: string | null;
  is_active?: boolean;
  scopes?: string[];
  total_calls?: number;
  total_cost_usd?: number;
}

interface ApiKeyResponse {
  api_keys?: ApiKey[];
  keys?: ApiKey[];
  items?: ApiKey[];
}

interface ModelEntry {
  slug: string;
  name: string;
  provider?: string;
  enabled: boolean;
  connected: boolean;
  context_window?: number;
  input_cost_per_1k?: number;
  output_cost_per_1k?: number;
  quantization?: string;
  route?: string;
}

interface ModelResponse {
  models?: unknown[];
  items?: unknown[];
}

async function fetchApiKeys(): Promise<ApiKey[]> {
  const resp = await api.get<ApiKeyResponse | ApiKey[]>("/workspace/api-keys");
  const data = resp.data;
  if (Array.isArray(data)) return data;
  return data.api_keys ?? data.keys ?? data.items ?? [];
}

async function fetchModels(): Promise<ModelEntry[]> {
  const resp = await api.get<ModelResponse | unknown[]>("/workspace/models");
  const data = resp.data;
  const rows = Array.isArray(data) ? data : data.models ?? data.items ?? [];
  return rows.map(normalizeModel).filter((model) => Boolean(model.slug));
}

async function toggleModel({ slug, enabled }: { slug: string; enabled: boolean }) {
  const resp = await api.patch<{ model_slug: string; enabled: boolean }>(
    `/workspace/models/${encodeURIComponent(slug)}`,
    { enabled },
  );
  return resp.data;
}

function normalizeModel(raw: unknown): ModelEntry {
  const row = raw as Record<string, unknown>;
  const slug = String(row.slug ?? row.model_slug ?? row.bedrock_model_id ?? "");
  const name = String(row.name ?? row.display_name ?? row.model_slug ?? row.slug ?? slug);
  const provider = row.provider ? String(row.provider) : undefined;
  const connected = row.connected !== false && String(row.status ?? "").toLowerCase() !== "disconnected";

  return {
    slug,
    name,
    provider,
    enabled: row.enabled !== false,
    connected,
    context_window: optionalNumber(row.context_window ?? row.context_length ?? row.context),
    input_cost_per_1k: normalizeUnitCost(row.input_cost_per_1k ?? row.input_cost_per_1m_tokens),
    output_cost_per_1k: normalizeUnitCost(row.output_cost_per_1k ?? row.output_cost_per_1m_tokens),
    quantization: row.quantization ? String(row.quantization) : undefined,
    route: inferRoute(provider),
  };
}

function optionalNumber(value: unknown): number | undefined {
  const n = Number(value);
  return Number.isFinite(n) ? n : undefined;
}

function normalizeUnitCost(value: unknown): number | undefined {
  const n = optionalNumber(value);
  if (n === undefined) return undefined;
  return n > 1 ? n / 1000 : n;
}

function inferRoute(provider?: string): string | undefined {
  const key = (provider ?? "").toLowerCase();
  if (!key) return undefined;
  if (key.includes("ollama") || key.includes("local")) return "primary";
  if (key.includes("groq") || key.includes("bedrock") || key.includes("aws")) return "approved fallback";
  return "workspace";
}

function apiErrorMessage(error: unknown, fallback: string) {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => (typeof item?.msg === "string" ? item.msg : null))
      .filter(Boolean)
      .join(", ");
  }
  return (error as Error)?.message ?? fallback;
}

export function SettingsPage() {
  const [tab, setTab] = useState<Tab>("identity");

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6">
      <header>
        <div className="mb-1 font-mono text-[11px] uppercase tracking-[0.15em] text-muted">
          Workspace / Settings
        </div>
        <h1 className="text-3xl font-semibold tracking-tight">Workspace administration</h1>
        <p className="mt-2 max-w-2xl text-sm text-bone-2">
          Operational identity, key inventory, and model governance. Sensitive changes route to their live owner
          screens so every action is backed by the production API.
        </p>
      </header>

      <nav className="v-card flex gap-1 p-1">
        <TabBtn active={tab === "identity"} onClick={() => setTab("identity")} icon={<Building2 className="h-4 w-4" />}>
          Identity
        </TabBtn>
        <TabBtn active={tab === "keys"} onClick={() => setTab("keys")} icon={<KeyRound className="h-4 w-4" />}>
          API keys
        </TabBtn>
        <TabBtn active={tab === "models"} onClick={() => setTab("models")} icon={<Box className="h-4 w-4" />}>
          Models
        </TabBtn>
      </nav>

      {tab === "identity" && <IdentityTab />}
      {tab === "keys" && <ApiKeysTab />}
      {tab === "models" && <ModelsTab />}
    </div>
  );
}

function TabBtn({
  active,
  onClick,
  icon,
  children,
}: {
  active: boolean;
  onClick: () => void;
  icon: ReactNode;
  children: ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-2 rounded-md px-3 py-1.5 text-[13px] font-medium transition",
        active ? "bg-brass/15 text-brass-2" : "text-bone-2 hover:bg-white/5 hover:text-bone",
      )}
    >
      {icon}
      {children}
    </button>
  );
}

function IdentityTab() {
  const user = useAuthStore((s) => s.user);
  const displayName = user?.full_name || user?.name || user?.email || "Signed-in user";

  return (
    <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <div className="v-card p-5">
        <div className="mb-3 flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
          <Building2 className="h-3 w-3" /> Workspace identity
        </div>
        <Field label="Workspace ID" value={user?.workspace_id ?? "-"} mono />
        <Field label="Workspace name" value={user?.workspace_name ?? "-"} />
        <Field label="Plan" value={user?.plan ?? "free evaluation"} />
        <Field label="Region" value={user?.region ?? "EU-sovereign"} />
      </div>

      <div className="v-card p-5">
        <div className="mb-3 flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
          <Shield className="h-3 w-3" /> Security posture
        </div>
        <Field label="mTLS internal" value="enforced" ok />
        <Field label="At-rest encryption" value="AES-256 sealed storage" ok />
        <Field label="MFA" value={user?.mfa_enabled ? "enabled" : "requires setup"} ok={user?.mfa_enabled} warn={!user?.mfa_enabled} />
        <Field label="HIPAA posture" value="BAA-ready controls" ok />
        {!user?.mfa_enabled && (
          <a
            className="mt-4 inline-flex items-center gap-2 rounded-lg border border-brass/35 bg-brass/10 px-3 py-2 text-[12px] font-semibold text-brass-2 hover:bg-brass/15"
            href="#/team"
          >
            Set up MFA in Team <ExternalLink className="h-3.5 w-3.5" />
          </a>
        )}
      </div>

      <div className="v-card p-5 lg:col-span-2">
        <div className="mb-3 flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
          <Cog className="h-3 w-3" /> Account
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <Field label="Signed in as" value={displayName} />
          <Field label="Email" value={user?.email ?? "-"} />
          <Field label="Role" value={user?.role ?? "user"} />
          <Field label="Last login" value={user?.last_login_at ? relativeTime(user.last_login_at) : "-"} />
          <Field label="User ID" value={user?.id ?? "-"} mono />
          <Field label="Superuser" value={user?.is_superuser ? "yes" : "no"} ok={Boolean(user?.is_superuser)} />
        </div>
      </div>
    </section>
  );
}

function Field({
  label,
  value,
  mono,
  ok,
  warn,
}: {
  label: string;
  value: string;
  mono?: boolean;
  ok?: boolean;
  warn?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-rule/50 py-2 last:border-0">
      <div className="text-[12px] text-muted">{label}</div>
      <div className={cn("flex min-w-0 items-center gap-1.5 truncate text-right text-[13px] text-bone", mono && "font-mono")}>
        {ok && <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-moss" />}
        {warn && <ShieldAlert className="h-3.5 w-3.5 shrink-0 text-brass-2" />}
        <span className="truncate">{value}</span>
      </div>
    </div>
  );
}

function ApiKeysTab() {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["workspace-api-keys"],
    queryFn: fetchApiKeys,
    refetchInterval: 30_000,
  });

  return (
    <section className="v-card p-0">
      <header className="flex items-center justify-between gap-4 border-b border-rule px-5 py-3">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
            API key inventory
          </div>
          <h3 className="mt-0.5 text-sm font-semibold">
            Live workspace keys used in the <span className="font-mono text-brass-2">X-API-Key</span> header
          </h3>
        </div>
        <a className="v-btn-ghost" href="#/vault">
          Open Vault <ExternalLink className="h-3.5 w-3.5" />
        </a>
      </header>

      {isError && (
        <ErrorStrip
          title="Failed to load keys"
          detail={apiErrorMessage(error, "Unknown error")}
          onRetry={() => refetch()}
        />
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-[13px]">
          <thead>
            <tr className="border-b border-rule font-mono text-[10px] uppercase tracking-wider text-muted">
              <th className="px-5 py-2 text-left font-medium">Name</th>
              <th className="px-5 py-2 text-left font-medium">Prefix</th>
              <th className="px-5 py-2 text-left font-medium">Status</th>
              <th className="px-5 py-2 text-right font-medium">Calls</th>
              <th className="px-5 py-2 text-right font-medium">Cost</th>
              <th className="px-5 py-2 text-right font-medium">Last used</th>
            </tr>
          </thead>
          <tbody className="font-mono">
            {isLoading && (
              <tr>
                <td colSpan={6} className="px-5 py-8 text-center text-muted">
                  loading...
                </td>
              </tr>
            )}
            {!isLoading && !isError && (!data || data.length === 0) && (
              <tr>
                <td colSpan={6} className="px-5 py-8 text-center text-muted">
                  No API keys yet. Use Vault to issue one for governed API access.
                </td>
              </tr>
            )}
            {data?.map((key) => (
              <tr key={key.id} className="border-b border-rule/60 last:border-0">
                <td className="px-5 py-2.5 text-bone">{key.name || "(unnamed)"}</td>
                <td className="px-5 py-2.5 text-muted">{key.key_prefix ?? `${key.id.slice(0, 8)}...`}</td>
                <td className="px-5 py-2.5">
                  <span className={cn("v-chip font-mono", key.is_active === false ? "v-chip-err" : "v-chip-ok")}>
                    {key.is_active === false ? "revoked" : "active"}
                  </span>
                </td>
                <td className="px-5 py-2.5 text-right text-bone-2">{(key.total_calls ?? 0).toLocaleString()}</td>
                <td className="px-5 py-2.5 text-right text-bone-2">${(key.total_cost_usd ?? 0).toFixed(6)}</td>
                <td className="px-5 py-2.5 text-right text-muted">
                  {key.last_used_at ? relativeTime(key.last_used_at) : "never"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function ModelsTab() {
  const qc = useQueryClient();
  const [toggleError, setToggleError] = useState<string | null>(null);
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["workspace-models"],
    queryFn: fetchModels,
    refetchInterval: 30_000,
  });

  const toggler = useMutation({
    mutationFn: toggleModel,
    onMutate: async ({ slug, enabled }) => {
      setToggleError(null);
      await qc.cancelQueries({ queryKey: ["workspace-models"] });
      const previous = qc.getQueryData<ModelEntry[]>(["workspace-models"]);
      qc.setQueryData<ModelEntry[]>(["workspace-models"], (current) =>
        (current ?? []).map((model) => (model.slug === slug ? { ...model, enabled } : model)),
      );
      return { previous };
    },
    onError: (err, _vars, context) => {
      if (context?.previous) qc.setQueryData(["workspace-models"], context.previous);
      setToggleError(apiErrorMessage(err, "The backend rejected the model update."));
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ["workspace-models"] }),
  });

  const sorted = useMemo(() => {
    if (!data) return [];
    return [...data].sort((a, b) => Number(!!b.enabled) - Number(!!a.enabled) || a.name.localeCompare(b.name));
  }, [data]);

  return (
    <section className="v-card p-0">
      <header className="flex items-center justify-between border-b border-rule px-5 py-3">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">Models</div>
          <h3 className="mt-0.5 text-sm font-semibold">Per-workspace routing and availability</h3>
          <p className="mt-1 text-xs text-muted">
            Toggles persist to <span className="font-mono">/workspace/models/:slug</span> and affect routing for
            authenticated workspace requests.
          </p>
        </div>
        <span className="v-chip font-mono">
          {data ? `${data.filter((m) => m.enabled).length} / ${data.length} on` : "-"}
        </span>
      </header>

      {toggleError && (
        <ErrorStrip title="Model toggle failed" detail={toggleError} onRetry={() => setToggleError(null)} retryLabel="Dismiss" />
      )}

      {isError && (
        <ErrorStrip
          title="Failed to load models"
          detail={apiErrorMessage(error, "Unknown error")}
          onRetry={() => refetch()}
        />
      )}

      <div className="divide-y divide-rule/50">
        {isLoading && (
          <div className="px-5 py-8 text-center font-mono text-[12px] text-muted">loading...</div>
        )}
        {!isLoading && !isError && sorted.length === 0 && (
          <div className="px-5 py-8 text-center font-mono text-[12px] text-muted">
            No models configured for this workspace.
          </div>
        )}
        {sorted.map((model) => {
          const isThisPending = toggler.isPending && toggler.variables?.slug === model.slug;
          return (
            <div key={model.slug} className="flex items-center gap-4 px-5 py-3">
              <div
                className={cn(
                  "flex h-9 w-9 items-center justify-center rounded-md",
                  model.connected ? "bg-electric/10 text-electric" : "bg-crimson/10 text-crimson",
                )}
              >
                <Box className="h-4 w-4" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <div className="truncate text-[14px] font-semibold text-bone">{model.name}</div>
                  <span className={cn("v-chip font-mono text-[10px]", model.connected ? "v-chip-ok" : "v-chip-err")}>
                    {model.connected ? "connected" : "not connected"}
                  </span>
                  {model.provider && <span className="v-chip font-mono text-[10px]">{model.provider}</span>}
                  {model.route && <span className="v-chip font-mono text-[10px]">{model.route}</span>}
                  {model.quantization && <span className="v-chip v-chip-brass font-mono text-[10px]">{model.quantization}</span>}
                </div>
                <div className="mt-0.5 font-mono text-[11px] text-muted">
                  {model.slug}
                  {model.context_window ? ` / ${model.context_window.toLocaleString()} ctx` : ""}
                  {model.input_cost_per_1k !== undefined ? ` / in $${model.input_cost_per_1k.toFixed(3)}/1K` : ""}
                  {model.output_cost_per_1k !== undefined ? ` / out $${model.output_cost_per_1k.toFixed(3)}/1K` : ""}
                </div>
              </div>
              <button
                onClick={() => toggler.mutate({ slug: model.slug, enabled: !model.enabled })}
                disabled={isThisPending}
                className={cn(
                  "relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition",
                  model.enabled ? "bg-moss/80" : "bg-rule",
                )}
                aria-pressed={model.enabled}
                aria-label={`Toggle ${model.slug}`}
              >
                <span
                  className={cn(
                    "inline-block h-5 w-5 translate-x-0.5 transform rounded-full bg-bone shadow transition",
                    model.enabled && "translate-x-5",
                  )}
                />
                {isThisPending && (
                  <Loader2 className="absolute left-1/2 top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 animate-spin text-muted" />
                )}
              </button>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function ErrorStrip({
  title,
  detail,
  onRetry,
  retryLabel = "Retry",
}: {
  title: string;
  detail: string;
  onRetry: () => void;
  retryLabel?: string;
}) {
  return (
    <div className="flex items-start gap-3 border-b border-rule bg-crimson/5 px-5 py-3 text-sm text-crimson">
      <AlertCircle className="mt-0.5 h-4 w-4" />
      <div className="flex-1">
        <div className="font-semibold">{title}</div>
        <div className="mt-0.5 text-xs opacity-80">{detail}</div>
      </div>
      <button className="v-btn-ghost" onClick={onRetry}>
        {retryLabel}
      </button>
    </div>
  );
}
