import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  Box,
  Building2,
  CheckCircle2,
  KeyRound,
  Loader2,
  Settings as Cog,
  Shield,
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
}

interface ApiKeyResponse {
  api_keys?: ApiKey[];
  keys?: ApiKey[];
  items?: ApiKey[];
}

interface ModelEntry {
  slug: string;
  name?: string;
  provider?: string;
  enabled?: boolean;
  context_window?: number;
  input_cost_per_1k?: number;
  output_cost_per_1k?: number;
  quantization?: string;
}

interface ModelResponse {
  models?: ModelEntry[];
  items?: ModelEntry[];
}

async function fetchApiKeys(): Promise<ApiKey[]> {
  const resp = await api.get<ApiKeyResponse | ApiKey[]>("/workspace/api-keys");
  const data = resp.data;
  if (Array.isArray(data)) return data;
  return data.api_keys ?? data.keys ?? data.items ?? [];
}

async function fetchModels(): Promise<ModelEntry[]> {
  const resp = await api.get<ModelResponse | ModelEntry[]>("/workspace/models");
  const data = resp.data;
  if (Array.isArray(data)) return data;
  return data.models ?? data.items ?? [];
}

async function toggleModel({ slug, enabled }: { slug: string; enabled: boolean }) {
  const resp = await api.patch(`/workspace/models/${encodeURIComponent(slug)}`, { enabled });
  return resp.data;
}

export function SettingsPage() {
  const [tab, setTab] = useState<Tab>("identity");

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6">
      <header>
        <div className="mb-1 font-mono text-[11px] uppercase tracking-[0.15em] text-muted">
          Workspace · Settings
        </div>
        <h1 className="text-3xl font-semibold tracking-tight">Workspace administration</h1>
        <p className="mt-2 max-w-2xl text-sm text-bone-2">
          Identity, API keys, model governance. Team roles, SAML/SCIM, and billing method ship in their own
          screens.
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
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-2 rounded-md px-3 py-1.5 text-[13px] font-medium transition",
        active
          ? "bg-brass/15 text-brass-2"
          : "text-bone-2 hover:bg-white/5 hover:text-bone",
      )}
    >
      {icon}
      {children}
    </button>
  );
}

function IdentityTab() {
  const user = useAuthStore((s) => s.user);
  return (
    <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <div className="v-card p-5">
        <div className="mb-3 flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
          <Building2 className="h-3 w-3" /> Workspace
        </div>
        <Field label="Workspace ID" value={user?.workspace_id ?? "—"} mono />
        <Field label="Workspace name" value={user?.workspace_name ?? "—"} />
        <Field label="Plan" value={user?.plan ?? "—"} />
        <Field label="Region" value={user?.region ?? "EU-sovereign"} />
      </div>

      <div className="v-card p-5">
        <div className="mb-3 flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
          <Shield className="h-3 w-3" /> Security posture
        </div>
        <Field label="mTLS internal" value="enforced" ok />
        <Field label="At-rest encryption" value="AES-256 (sovereign KMS)" ok />
        <Field label="SOC 2 readiness" value="Type II evidence on schedule" ok />
        <Field label="HIPAA posture" value="BAA-ready" ok />
        <div className="mt-4 rounded-lg border border-rule p-3 text-[12px] text-bone-2">
          Full posture report lives in{" "}
          <a className="text-brass-2 hover:underline" href="#/compliance">
            Compliance
          </a>
          .
        </div>
      </div>

      <div className="v-card p-5 lg:col-span-2">
        <div className="mb-3 flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
          <Cog className="h-3 w-3" /> Account
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <Field label="Signed in as" value={user?.email ?? "—"} />
          <Field label="Role" value={user?.role ?? "owner"} />
          <Field label="Last login" value={user?.last_login_at ? relativeTime(user.last_login_at) : "—"} />
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
}: {
  label: string;
  value: string;
  mono?: boolean;
  ok?: boolean;
}) {
  return (
    <div className="flex items-center justify-between border-b border-rule/50 py-2 last:border-0">
      <div className="text-[12px] text-muted">{label}</div>
      <div className={cn("flex items-center gap-1.5 text-[13px] text-bone", mono && "font-mono")}>
        {ok && <CheckCircle2 className="h-3.5 w-3.5 text-moss" />}
        {value}
      </div>
    </div>
  );
}

function ApiKeysTab() {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["workspace-api-keys"],
    queryFn: fetchApiKeys,
  });

  return (
    <section className="v-card p-0">
      <header className="flex items-center justify-between border-b border-rule px-5 py-3">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
            API keys
          </div>
          <h3 className="mt-0.5 text-sm font-semibold">
            Programmatic access — used in <span className="font-mono text-brass-2">X-API-Key</span> header
          </h3>
        </div>
        <button className="v-btn-ghost" disabled title="Creation flow ships in the Vault page">
          + Issue key
        </button>
      </header>

      {isError && (
        <div className="flex items-start gap-3 border-b border-rule bg-crimson/5 px-5 py-3 text-sm text-crimson">
          <AlertCircle className="mt-0.5 h-4 w-4" />
          <div className="flex-1">
            <div className="font-semibold">Failed to load keys</div>
            <div className="mt-0.5 text-xs opacity-80">
              {(error as Error)?.message ?? "Unknown error"}
            </div>
          </div>
          <button className="v-btn-ghost" onClick={() => refetch()}>
            Retry
          </button>
        </div>
      )}

      <table className="w-full text-[13px]">
        <thead>
          <tr className="border-b border-rule font-mono text-[10px] uppercase tracking-wider text-muted">
            <th className="px-5 py-2 text-left font-medium">Name</th>
            <th className="px-5 py-2 text-left font-medium">Prefix</th>
            <th className="px-5 py-2 text-left font-medium">Status</th>
            <th className="px-5 py-2 text-right font-medium">Created</th>
            <th className="px-5 py-2 text-right font-medium">Last used</th>
          </tr>
        </thead>
        <tbody className="font-mono">
          {isLoading && (
            <tr>
              <td colSpan={5} className="px-5 py-8 text-center text-muted">
                loading…
              </td>
            </tr>
          )}
          {!isLoading && !isError && (!data || data.length === 0) && (
            <tr>
              <td colSpan={5} className="px-5 py-8 text-center text-muted">
                No API keys yet.
              </td>
            </tr>
          )}
          {data?.map((k) => (
            <tr key={k.id} className="border-b border-rule/60 last:border-0">
              <td className="px-5 py-2.5 text-bone">{k.name || "(unnamed)"}</td>
              <td className="px-5 py-2.5 text-muted">{k.key_prefix ?? k.id.slice(0, 8) + "…"}</td>
              <td className="px-5 py-2.5">
                <span
                  className={cn(
                    "v-chip font-mono",
                    k.is_active === false ? "v-chip-err" : "v-chip-ok",
                  )}
                >
                  {k.is_active === false ? "revoked" : "active"}
                </span>
              </td>
              <td className="px-5 py-2.5 text-right text-bone-2">{relativeTime(k.created_at)}</td>
              <td className="px-5 py-2.5 text-right text-muted">
                {k.last_used_at ? relativeTime(k.last_used_at) : "never"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function ModelsTab() {
  const qc = useQueryClient();
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["workspace-models"],
    queryFn: fetchModels,
  });
  const toggler = useMutation({
    mutationFn: toggleModel,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workspace-models"] }),
  });

  const sorted = useMemo(() => {
    if (!data) return [];
    return [...data].sort((a, b) => Number(!!b.enabled) - Number(!!a.enabled));
  }, [data]);

  return (
    <section className="v-card p-0">
      <header className="flex items-center justify-between border-b border-rule px-5 py-3">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">Models</div>
          <h3 className="mt-0.5 text-sm font-semibold">
            Per-workspace routing &amp; availability
          </h3>
        </div>
        <span className="v-chip font-mono">
          {data ? `${data.filter((m) => m.enabled).length} / ${data.length} on` : "—"}
        </span>
      </header>

      {isError && (
        <div className="flex items-start gap-3 border-b border-rule bg-crimson/5 px-5 py-3 text-sm text-crimson">
          <AlertCircle className="mt-0.5 h-4 w-4" />
          <div className="flex-1">
            <div className="font-semibold">Failed to load models</div>
            <div className="mt-0.5 text-xs opacity-80">
              {(error as Error)?.message ?? "Unknown error"}
            </div>
          </div>
          <button className="v-btn-ghost" onClick={() => refetch()}>
            Retry
          </button>
        </div>
      )}

      <div className="divide-y divide-rule/50">
        {isLoading && (
          <div className="px-5 py-8 text-center font-mono text-[12px] text-muted">loading…</div>
        )}
        {!isLoading && !isError && sorted.length === 0 && (
          <div className="px-5 py-8 text-center font-mono text-[12px] text-muted">
            No models configured.
          </div>
        )}
        {sorted.map((m) => (
          <div key={m.slug} className="flex items-center gap-4 px-5 py-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-md bg-electric/10 text-electric">
              <Box className="h-4 w-4" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <div className="truncate text-[14px] font-semibold text-bone">
                  {m.name ?? m.slug}
                </div>
                {m.quantization && (
                  <span className="v-chip v-chip-brass font-mono text-[10px]">
                    {m.quantization}
                  </span>
                )}
                {m.provider && (
                  <span className="v-chip font-mono text-[10px]">{m.provider}</span>
                )}
              </div>
              <div className="mt-0.5 font-mono text-[11px] text-muted">
                {m.slug}
                {m.context_window ? ` · ${m.context_window.toLocaleString()} ctx` : ""}
                {m.input_cost_per_1k ? ` · in $${m.input_cost_per_1k.toFixed(3)}/1k` : ""}
                {m.output_cost_per_1k ? ` · out $${m.output_cost_per_1k.toFixed(3)}/1k` : ""}
              </div>
            </div>
            <button
              onClick={() => toggler.mutate({ slug: m.slug, enabled: !m.enabled })}
              disabled={toggler.isPending}
              className={cn(
                "relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition",
                m.enabled ? "bg-moss/80" : "bg-rule",
              )}
              aria-pressed={m.enabled}
              aria-label={`Toggle ${m.slug}`}
            >
              <span
                className={cn(
                  "inline-block h-5 w-5 translate-x-0.5 transform rounded-full bg-bone shadow transition",
                  m.enabled && "translate-x-5",
                )}
              />
              {toggler.isPending && (
                <Loader2 className="absolute left-1/2 top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 animate-spin text-muted" />
              )}
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}
