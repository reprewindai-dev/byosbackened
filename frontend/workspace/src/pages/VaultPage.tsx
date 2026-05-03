import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  Check,
  Copy,
  KeyRound,
  Loader2,
  Lock,
  Plus,
  ShieldCheck,
  Trash2,
  X,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn, relativeTime } from "@/lib/cn";

interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  rate_limit_per_minute: number;
  is_active: boolean;
  created_at: string;
  expires_at: string | null;
  last_used_at: string | null;
}

interface ApiKeyCreateResponse extends ApiKey {
  raw_key: string;
}

const AVAILABLE_SCOPES = ["read", "exec", "write", "admin"] as const;

async function listKeys(): Promise<ApiKey[]> {
  const resp = await api.get<ApiKey[]>("/auth/api-keys");
  return resp.data;
}

async function createKey(payload: {
  name: string;
  scopes: string[];
  rate_limit_per_minute: number;
  expires_in_days: number | null;
}) {
  const body = {
    ...payload,
    expires_in_days: payload.expires_in_days,
  };
  const resp = await api.post<ApiKeyCreateResponse>("/auth/api-keys", body);
  return resp.data;
}

async function revokeKey(id: string) {
  await api.delete(`/auth/api-keys/${encodeURIComponent(id)}`);
}

export function VaultPage() {
  const qc = useQueryClient();
  const keys = useQuery({ queryKey: ["vault-api-keys"], queryFn: listKeys });

  const [creating, setCreating] = useState(false);
  const [justCreated, setJustCreated] = useState<ApiKeyCreateResponse | null>(null);

  const create = useMutation({
    mutationFn: createKey,
    onSuccess: (data) => {
      setJustCreated(data);
      setCreating(false);
      qc.invalidateQueries({ queryKey: ["vault-api-keys"] });
    },
  });

  const revoke = useMutation({
    mutationFn: revokeKey,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["vault-api-keys"] }),
  });

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-1 font-mono text-[11px] uppercase tracking-[0.15em] text-muted">
            Workspace · Vault
          </div>
          <h1 className="text-3xl font-semibold tracking-tight">Sovereign secret store</h1>
          <p className="mt-2 max-w-2xl text-sm text-bone-2">
            API keys and integration credentials, sealed at rest with AES-256, injected at runtime, never written
            to disk. Each key is scoped, rate-limited, and tracked through every request.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <span className="v-chip v-chip-ok">
              <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-moss" />
              live · <span className="font-mono">/api/v1/auth/api-keys</span>
            </span>
            <span className="v-chip">AES-256 sealed</span>
            <span className="v-chip">runtime injection only</span>
          </div>
        </div>
        <button className="v-btn-primary" onClick={() => setCreating(true)} disabled={creating}>
          <Plus className="h-4 w-4" /> Issue new key
        </button>
      </header>

      {justCreated && <JustCreatedBanner item={justCreated} onDismiss={() => setJustCreated(null)} />}

      <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCell
          icon={<KeyRound className="h-3 w-3" />}
          label="Active keys"
          value={String(keys.data?.filter((k) => k.is_active).length ?? 0)}
        />
        <StatCell
          icon={<Lock className="h-3 w-3" />}
          label="Revoked"
          value={String(keys.data?.filter((k) => !k.is_active).length ?? 0)}
        />
        <StatCell
          icon={<ShieldCheck className="h-3 w-3" />}
          label="At-rest cipher"
          value="AES-256"
        />
        <StatCell
          icon={<ShieldCheck className="h-3 w-3" />}
          label="In-transit"
          value="TLS 1.3 / mTLS"
        />
      </section>

      {keys.isError && (
        <div className="v-card flex items-start gap-3 border-crimson/40 bg-crimson/5 p-4 text-sm text-crimson">
          <AlertCircle className="mt-0.5 h-4 w-4" />
          <div className="flex-1">
            <div className="font-semibold">Failed to load vault</div>
            <div className="mt-0.5 text-xs opacity-80">{(keys.error as Error)?.message ?? "Unknown"}</div>
          </div>
          <button className="v-btn-ghost" onClick={() => keys.refetch()}>
            Retry
          </button>
        </div>
      )}

      <section className="v-card p-0">
        <header className="flex items-center justify-between border-b border-rule px-5 py-3">
          <div>
            <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
              API keys
            </div>
            <h3 className="mt-0.5 text-sm font-semibold">
              Used in <span className="font-mono text-brass-2">X-API-Key</span> header for /v1/exec and tool calls
            </h3>
          </div>
        </header>

        <table className="w-full text-[13px]">
          <thead>
            <tr className="border-b border-rule font-mono text-[10px] uppercase tracking-wider text-muted">
              <th className="px-5 py-2 text-left font-medium">Name</th>
              <th className="px-5 py-2 text-left font-medium">Prefix</th>
              <th className="px-5 py-2 text-left font-medium">Scopes</th>
              <th className="px-5 py-2 text-right font-medium">Rate</th>
              <th className="px-5 py-2 text-right font-medium">Last used</th>
              <th className="px-5 py-2 text-right font-medium">Status</th>
              <th className="px-5 py-2 text-right font-medium" />
            </tr>
          </thead>
          <tbody className="font-mono">
            {keys.isLoading && (
              <tr>
                <td colSpan={7} className="px-5 py-8 text-center text-muted">
                  loading…
                </td>
              </tr>
            )}
            {!keys.isLoading && keys.data?.length === 0 && (
              <tr>
                <td colSpan={7} className="px-5 py-8 text-center text-muted">
                  No keys yet. Issue one to call the execution API.
                </td>
              </tr>
            )}
            {keys.data?.map((k) => (
              <tr key={k.id} className="border-b border-rule/60 last:border-0">
                <td className="px-5 py-2.5 text-bone">{k.name}</td>
                <td className="px-5 py-2.5 text-muted">{k.key_prefix}…</td>
                <td className="px-5 py-2.5">
                  <div className="flex flex-wrap gap-1">
                    {k.scopes.map((s) => (
                      <span key={s} className="v-chip font-mono text-[10px]">
                        {s}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-5 py-2.5 text-right text-bone-2">{k.rate_limit_per_minute}/min</td>
                <td className="px-5 py-2.5 text-right text-muted">
                  {k.last_used_at ? relativeTime(k.last_used_at) : "never"}
                </td>
                <td className="px-5 py-2.5 text-right">
                  <span className={cn("v-chip font-mono", k.is_active ? "v-chip-ok" : "v-chip-err")}>
                    {k.is_active ? "active" : "revoked"}
                  </span>
                </td>
                <td className="px-5 py-2.5 text-right">
                  {k.is_active && (
                    <button
                      className="v-btn-ghost text-crimson hover:bg-crimson/10"
                      onClick={() => {
                        if (
                          confirm(`Revoke “${k.name}”? This cannot be undone. Active integrations will fail.`)
                        ) {
                          revoke.mutate(k.id);
                        }
                      }}
                      disabled={revoke.isPending}
                    >
                      <Trash2 className="h-3.5 w-3.5" /> Revoke
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {creating && (
        <CreateKeyModal
          onClose={() => setCreating(false)}
          onCreate={(payload) => create.mutate(payload)}
          pending={create.isPending}
          error={create.error ? (create.error as Error).message : null}
        />
      )}
    </div>
  );
}

function StatCell({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="v-card p-4">
      <div className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.1em] text-muted">
        {icon}
        {label}
      </div>
      <div className="mt-1.5 text-xl font-semibold text-bone">{value}</div>
    </div>
  );
}

function JustCreatedBanner({
  item,
  onDismiss,
}: {
  item: ApiKeyCreateResponse;
  onDismiss: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(item.raw_key).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };
  return (
    <div className="v-card border-brass/50 bg-brass/5 p-5">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.12em] text-brass-2">
          <KeyRound className="h-3 w-3" />
          Secret issued — copy now, it will never be shown again
        </div>
        <button
          onClick={onDismiss}
          className="rounded p-1 text-muted hover:bg-white/5 hover:text-bone"
          aria-label="Dismiss"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="mt-2 flex items-center gap-2 rounded-md border border-rule bg-ink-2 px-3 py-2">
        <code className="flex-1 break-all font-mono text-[12px] text-bone">{item.raw_key}</code>
        <button
          className={cn("v-btn-ghost shrink-0", copied && "text-moss")}
          onClick={copy}
        >
          {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <div className="mt-2 font-mono text-[11px] text-muted">
        Key <span className="text-bone">{item.name}</span> · prefix{" "}
        <span className="text-bone">{item.key_prefix}…</span> · scopes {item.scopes.join(", ")}
      </div>
    </div>
  );
}

function CreateKeyModal({
  onClose,
  onCreate,
  pending,
  error,
}: {
  onClose: () => void;
  onCreate: (p: {
    name: string;
    scopes: string[];
    rate_limit_per_minute: number;
    expires_in_days: number | null;
  }) => void;
  pending: boolean;
  error: string | null;
}) {
  const [name, setName] = useState("");
  const [scopes, setScopes] = useState<string[]>(["read", "exec"]);
  const [rate, setRate] = useState(60);
  const [expiry, setExpiry] = useState<string>("90");

  const toggleScope = (s: string) => {
    setScopes((prev) => (prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]));
  };

  const submit = () => {
    if (!name.trim()) return;
    onCreate({
      name: name.trim(),
      scopes,
      rate_limit_per_minute: rate,
      expires_in_days: expiry === "never" ? null : parseInt(expiry, 10),
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
      <button className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} aria-label="Close" />
      <div className="relative w-full max-w-md rounded-xl border border-rule bg-ink-1 p-5 shadow-2xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Issue API key</h2>
          <button
            onClick={onClose}
            className="rounded p-1 text-muted hover:bg-white/5 hover:text-bone"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="v-label" htmlFor="key-name">
              Name
            </label>
            <input
              id="key-name"
              className="v-input"
              placeholder="e.g. production-backend"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
            />
          </div>

          <div>
            <div className="v-label">Scopes</div>
            <div className="flex flex-wrap gap-2">
              {AVAILABLE_SCOPES.map((s) => {
                const on = scopes.includes(s);
                return (
                  <button
                    key={s}
                    onClick={() => toggleScope(s)}
                    className={cn(
                      "rounded-md border px-3 py-1 font-mono text-[12px] transition",
                      on
                        ? "border-brass/50 bg-brass/15 text-brass-2"
                        : "border-rule bg-white/[0.02] text-muted hover:text-bone",
                    )}
                  >
                    {s}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="v-label" htmlFor="rate">
                Rate limit / min
              </label>
              <input
                id="rate"
                type="number"
                className="v-input"
                value={rate}
                min={1}
                max={10000}
                onChange={(e) => setRate(parseInt(e.target.value || "60", 10))}
              />
            </div>
            <div>
              <label className="v-label" htmlFor="expiry">
                Expires
              </label>
              <select
                id="expiry"
                className="v-input"
                value={expiry}
                onChange={(e) => setExpiry(e.target.value)}
              >
                <option value="30">30 days</option>
                <option value="90">90 days</option>
                <option value="365">1 year</option>
                <option value="never">Never (not recommended)</option>
              </select>
            </div>
          </div>

          {error && (
            <div className="flex items-start gap-2 rounded-md border border-crimson/40 bg-crimson/5 p-3 text-[12px] text-crimson">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              {error}
            </div>
          )}

          <div className="flex gap-2">
            <button className="v-btn-ghost flex-1" onClick={onClose} disabled={pending}>
              Cancel
            </button>
            <button
              className="v-btn-primary flex-1"
              onClick={submit}
              disabled={pending || !name.trim() || scopes.length === 0}
            >
              {pending && <Loader2 className="h-4 w-4 animate-spin" />}
              {pending ? "Issuing…" : "Issue key"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
