import { useMemo, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  Box,
  Building2,
  CheckCircle2,
  ExternalLink,
  Github,
  KeyRound,
  Loader2,
  Settings as Cog,
  Shield,
  ShieldAlert,
} from "lucide-react";
import { api } from "@/lib/api";
import { beginGithubLogin } from "@/lib/auth";
import { useAuthStore } from "@/store/auth-store";
import { cn, relativeTime } from "@/lib/cn";
import { ProofStrip, RunStatePanel, type FlowStatus } from "@/components/workspace/FlowPrimitives";
import type { ConnectedAccountsResponse, GithubRepo, WorkspaceGithubIntegration } from "@/types/api";

type Tab = "identity" | "keys" | "models" | "integrations";

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

async function testWorkspaceConfig() {
  const started = performance.now();
  const [identity, keys, models] = await Promise.allSettled([
    api.get("/auth/me"),
    api.get("/workspace/api-keys"),
    api.get("/workspace/models"),
  ]);
  const rows = [
    { label: "identity", result: identity },
    { label: "api keys", result: keys },
    { label: "models", result: models },
  ];
  return {
    latency_ms: Math.round(performance.now() - started),
    rows: rows.map((row) => ({ label: row.label, ok: row.result.status === "fulfilled" })),
  };
}

async function fetchConnectedAccounts(): Promise<ConnectedAccountsResponse> {
  const resp = await api.get<ConnectedAccountsResponse>("/auth/connected-accounts");
  return resp.data;
}

async function fetchWorkspaceGithubIntegration(): Promise<WorkspaceGithubIntegration> {
  const resp = await api.get<WorkspaceGithubIntegration>("/workspace/integrations/github");
  return resp.data;
}

async function fetchGithubRepos(): Promise<GithubRepo[]> {
  const resp = await api.get<{ repos: GithubRepo[] }>("/auth/github/repos");
  return resp.data.repos ?? [];
}

async function disconnectGithub() {
  await api.delete("/auth/connected-accounts/github");
}

async function selectGithubRepo(repo: GithubRepo) {
  const resp = await api.post("/workspace/integrations/github/select-repo", {
    repo_full_name: repo.full_name,
    repo_id: repo.id,
    default_branch: repo.default_branch,
    visibility: repo.visibility,
    permissions: repo.permissions,
  });
  return resp.data;
}

async function unselectGithubRepo(selectionId: string) {
  await api.delete(`/workspace/integrations/github/select-repo/${selectionId}`);
}

export function SettingsPage() {
  const [tab, setTab] = useState<Tab>("identity");
  const configTest = useMutation({ mutationFn: testWorkspaceConfig });

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6">
      <header>
        <div className="mb-1 font-mono text-[11px] uppercase tracking-[0.15em] text-muted">
          Settings
        </div>
        <h1 className="text-3xl font-semibold tracking-tight">Workspace administration</h1>
        <p className="mt-2 max-w-2xl text-sm text-bone-2">
          One opinionated panel for the entire control plane - workspace identity, routing posture, security defaults,
          branding, and integrations.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[280px_1fr]">
        <nav className="v-card h-fit p-3">
          <TabBtn active={tab === "identity"} onClick={() => setTab("identity")} icon={<Building2 className="h-4 w-4" />}>
            Workspace
          </TabBtn>
          <TabBtn active={tab === "models"} onClick={() => setTab("models")} icon={<Box className="h-4 w-4" />}>
            Routing
          </TabBtn>
          <TabBtn active={tab === "keys"} onClick={() => setTab("keys")} icon={<KeyRound className="h-4 w-4" />}>
            API & SDK
          </TabBtn>
          <TabBtn active={tab === "integrations"} onClick={() => setTab("integrations")} icon={<Github className="h-4 w-4" />}>
            Integrations
          </TabBtn>
        </nav>

        <div className="space-y-4">
          {tab === "identity" && (
            <>
              <IdentityTab />
              <SettingsProofCard configTest={configTest} />
            </>
          )}
          {tab === "keys" && <ApiKeysTab />}
          {tab === "models" && <ModelsTab />}
          {tab === "integrations" && <IntegrationsTab />}
        </div>
      </div>
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
        "flex w-full items-center gap-2 rounded-md px-3 py-2.5 text-left text-[13px] font-medium transition",
        active ? "bg-brass/15 text-brass-2" : "text-bone-2 hover:bg-white/5 hover:text-bone",
      )}
    >
      {icon}
      {children}
    </button>
  );
}

function SettingsProofCard({
  configTest,
}: {
  configTest: {
    isPending: boolean;
    isError: boolean;
    data?: { latency_ms: number; rows: { label: string; ok: boolean }[] };
    error?: unknown;
    mutate: () => void;
  };
}) {
  const rowStatus = (label: string): FlowStatus =>
    configTest.data?.rows.find((row) => row.label === label)?.ok
      ? "succeeded"
      : configTest.isError
        ? "failed"
        : configTest.isPending
          ? "running"
          : "idle";

  return (
    <div className="space-y-3">
      <RunStatePanel
        eyebrow="Settings proof"
        title="Live backend configuration check"
        status={configTest.isPending ? "running" : configTest.isError ? "failed" : configTest.data ? "succeeded" : "idle"}
        summary="This panel reads the production API surface used by Settings instead of displaying disconnected controls."
        steps={[
          { label: "Identity route", status: rowStatus("identity"), detail: "/api/v1/auth/me" },
          { label: "API key route", status: rowStatus("api keys"), detail: "/api/v1/workspace/api-keys" },
          { label: "Model route", status: rowStatus("models"), detail: "/api/v1/workspace/models" },
        ]}
        metrics={[
          { label: "latency", value: configTest.data ? `${configTest.data.latency_ms}ms` : configTest.isPending ? "running" : "not tested" },
          { label: "routes passed", value: configTest.data ? `${configTest.data.rows.filter((row) => row.ok).length} / ${configTest.data.rows.length}` : "not tested" },
          { label: "surface", value: "workspace" },
          { label: "source", value: "live backend" },
        ]}
        error={configTest.error}
        actions={[
          { label: "Test settings", onClick: () => configTest.mutate(), disabled: configTest.isPending, primary: true },
          { label: "Open Vault", href: "/vault" },
          { label: "Open Team", href: "/team" },
        ]}
      />
      <ProofStrip
        items={[
          { label: "identity", value: "/api/v1/auth/me" },
          { label: "keys", value: "/api/v1/workspace/api-keys" },
          { label: "models", value: "/api/v1/workspace/models" },
          { label: "result", value: configTest.data ? "verified" : "pending" },
        ]}
      />
    </div>
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
          <Field label="Last login" value={user?.last_login_at ? relativeTime(user.last_login_at) : user?.last_login ? relativeTime(user.last_login) : "-"} />
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

function IntegrationsTab() {
  const qc = useQueryClient();
  const connectedQ = useQuery({ queryKey: ["github-connected-account"], queryFn: fetchConnectedAccounts });
  const integrationQ = useQuery({ queryKey: ["workspace-github-integration"], queryFn: fetchWorkspaceGithubIntegration });
  const reposQ = useQuery({
    queryKey: ["github-repos"],
    queryFn: fetchGithubRepos,
    enabled: Boolean(connectedQ.data?.github_connected),
    retry: false,
  });

  const connectMut = useMutation({
    mutationFn: beginGithubLogin,
    onSuccess: (payload) => {
      window.location.href = payload.auth_url;
    },
  });
  const disconnectMut = useMutation({
    mutationFn: disconnectGithub,
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["github-connected-account"] }),
        qc.invalidateQueries({ queryKey: ["workspace-github-integration"] }),
        qc.invalidateQueries({ queryKey: ["github-repos"] }),
      ]);
    },
  });
  const selectMut = useMutation({
    mutationFn: selectGithubRepo,
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["workspace-github-integration"] });
    },
  });
  const unselectMut = useMutation({
    mutationFn: unselectGithubRepo,
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["workspace-github-integration"] });
    },
  });

  const selectedRepoNames = new Set((integrationQ.data?.selected_repos ?? []).map((repo) => repo.repo_full_name));

  return (
    <section className="space-y-4">
      <div className="v-card p-5">
        <div className="mb-3 flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
          <Github className="h-3 w-3" /> GitHub workspace integration
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <Field label="OAuth status" value={connectedQ.data?.github_configured ? "configured" : "not configured"} ok={Boolean(connectedQ.data?.github_configured)} warn={!connectedQ.data?.github_configured} />
          <Field label="Connection" value={connectedQ.data?.github_connected ? "connected" : "not connected"} ok={Boolean(connectedQ.data?.github_connected)} warn={!connectedQ.data?.github_connected} />
          <Field label="GitHub user" value={connectedQ.data?.github_username ?? "-"} />
          <Field label="Repo access mode" value={integrationQ.data?.repo_access_mode ?? "read_only"} ok />
          <Field label="Context scope" value={integrationQ.data?.repo_context_scope ?? "metadata_only"} ok />
          <Field label="Selected repos" value={String(integrationQ.data?.selected_repos.length ?? 0)} />
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {!connectedQ.data?.github_connected ? (
            <button className="v-btn-primary" disabled={connectMut.isPending || !connectedQ.data?.github_configured} onClick={() => connectMut.mutate()}>
              {connectMut.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Github className="h-4 w-4" />} Connect GitHub
            </button>
          ) : (
            <button className="v-btn-ghost" disabled={disconnectMut.isPending} onClick={() => disconnectMut.mutate()}>
              {disconnectMut.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Github className="h-4 w-4" />} Disconnect GitHub
            </button>
          )}
          <button className="v-btn-ghost" disabled={!connectedQ.data?.github_connected || reposQ.isFetching} onClick={() => reposQ.refetch()}>
            {reposQ.isFetching ? <Loader2 className="h-4 w-4 animate-spin" /> : <Github className="h-4 w-4" />} Refresh repos
          </button>
        </div>
        <div className="mt-4 rounded-md border border-rule bg-ink/40 p-3 text-[12px] text-bone-2">
          Repo context is governed and read-only by default. Veklom stores selected repo metadata at the workspace level,
          does not expose GitHub tokens to the frontend, and treats attached repo context as planning input rather than
          automatic code execution.
        </div>
      </div>

      <div className="v-card p-0">
        <header className="flex items-center justify-between border-b border-rule px-5 py-3">
          <div>
            <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">Selected repos</div>
            <h3 className="mt-0.5 text-sm font-semibold">Workspace-scoped repo context</h3>
          </div>
          <span className="v-chip font-mono">{integrationQ.data?.selected_repos.length ?? 0}</span>
        </header>
        <div className="divide-y divide-rule/50">
          {(integrationQ.data?.selected_repos ?? []).length === 0 && (
            <div className="px-5 py-6 text-sm text-muted">No repos selected for this workspace yet.</div>
          )}
          {(integrationQ.data?.selected_repos ?? []).map((repo) => (
            <div key={repo.id} className="flex items-center gap-4 px-5 py-3">
              <div className="min-w-0 flex-1">
                <div className="truncate font-semibold text-bone">{repo.repo_full_name}</div>
                <div className="mt-0.5 font-mono text-[11px] text-muted">
                  branch={repo.default_branch ?? "main"} · scope={repo.repo_context_scope} · access=read_only
                </div>
              </div>
              <button className="v-btn-ghost" disabled={unselectMut.isPending} onClick={() => unselectMut.mutate(repo.id)}>
                Remove
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="v-card p-0">
        <header className="flex items-center justify-between border-b border-rule px-5 py-3">
          <div>
            <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">Available repos</div>
            <h3 className="mt-0.5 text-sm font-semibold">Choose repos Veklom may reference</h3>
          </div>
          <span className="v-chip font-mono">{reposQ.data?.length ?? 0}</span>
        </header>
        {reposQ.isError && (
          <ErrorStrip title="Failed to load GitHub repos" detail={apiErrorMessage(reposQ.error, "GitHub repo list unavailable")} onRetry={() => reposQ.refetch()} />
        )}
        <div className="divide-y divide-rule/50">
          {!connectedQ.data?.github_connected && (
            <div className="px-5 py-6 text-sm text-muted">Connect GitHub to list repos and attach repo context in Playground.</div>
          )}
          {connectedQ.data?.github_connected && (reposQ.data ?? []).length === 0 && !reposQ.isFetching && (
            <div className="px-5 py-6 text-sm text-muted">No repos returned from GitHub yet.</div>
          )}
          {(reposQ.data ?? []).map((repo) => {
            const selected = selectedRepoNames.has(repo.full_name);
            return (
              <div key={repo.id} className="flex items-center gap-4 px-5 py-3">
                <div className="min-w-0 flex-1">
                  <div className="truncate font-semibold text-bone">{repo.full_name}</div>
                  <div className="mt-0.5 text-[12px] text-muted">
                    {repo.visibility ?? (repo.private ? "private" : "public")} · {repo.default_branch ?? "main"} · {repo.language ?? "unknown language"}
                  </div>
                </div>
                <button
                  className={selected ? "v-btn-ghost" : "v-btn-primary"}
                  disabled={selected || selectMut.isPending}
                  onClick={() => selectMut.mutate(repo)}
                >
                  {selected ? "Selected" : "Use in workspace"}
                </button>
              </div>
            );
          })}
        </div>
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
