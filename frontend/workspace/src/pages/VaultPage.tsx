import { useMemo, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  Check,
  CheckCircle2,
  Clock3,
  Copy,
  KeyRound,
  Loader2,
  Lock,
  MoreHorizontal,
  Plus,
  RotateCcw,
  Search,
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
  const resp = await api.post<ApiKeyCreateResponse>("/auth/api-keys", payload);
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
  const [selectedKey, setSelectedKey] = useState<ApiKey | null>(null);
  const [search, setSearch] = useState("");

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

  const allKeys = keys.data ?? [];
  const filteredKeys = useMemo(() => filterKeys(allKeys, search), [allKeys, search]);
  const active = allKeys.filter((key) => key.is_active).length;
  const revoked = allKeys.filter((key) => !key.is_active).length;
  const expiring = allKeys.filter((key) => key.expires_at && daysUntil(key.expires_at) <= 30).length;

  return (
    <div className="mx-auto w-full max-w-[1400px]">
      <PageHeader active={active} revoked={revoked} expiring={expiring} onNew={() => setCreating(true)} />

      {justCreated && <JustCreatedBanner item={justCreated} onDismiss={() => setJustCreated(null)} />}

      {keys.isError && (
        <div className="frame mb-4 flex items-start gap-3 border-crimson/40 bg-crimson/5 p-4 text-sm text-crimson">
          <AlertCircle className="mt-0.5 h-4 w-4" />
          <div className="flex-1">
            <div className="font-semibold">Failed to load vault</div>
            <div className="mt-0.5 text-xs opacity-80">{(keys.error as Error)?.message ?? "Unknown"}</div>
          </div>
          <button className="v-btn-ghost h-8 px-3 text-xs" onClick={() => keys.refetch()}>
            Retry
          </button>
        </div>
      )}

      <section>
        <SecretsTable
          keys={filteredKeys}
          loading={keys.isLoading}
          query={search}
          onQuery={setSearch}
          active={active}
          revoked={revoked}
          expiring={expiring}
          revokePending={revoke.isPending}
          onInspect={setSelectedKey}
          onRevoke={(key) => {
            if (window.confirm(`Revoke "${key.name}"? Active integrations using this key will fail.`)) {
              revoke.mutate(key.id);
            }
          }}
        />

        <div className="mt-4 grid grid-cols-12 gap-4">
          <ApiKeysPanel keys={filteredKeys} />
          <VaultPosture active={active} revoked={revoked} expiring={expiring} total={allKeys.length} />
        </div>
      </section>

      {creating && (
        <CreateKeyModal
          onClose={() => setCreating(false)}
          onCreate={(payload) => create.mutate(payload)}
          pending={create.isPending}
          error={create.error ? (create.error as Error).message : null}
        />
      )}

      {selectedKey && <KeyDetailDrawer item={selectedKey} onClose={() => setSelectedKey(null)} />}
    </div>
  );
}

function PageHeader({
  active,
  revoked,
  expiring,
  onNew,
}: {
  active: number;
  revoked: number;
  expiring: number;
  onNew: () => void;
}) {
  return (
    <header className="mb-5 flex flex-wrap items-start justify-between gap-4">
      <div>
        <div className="text-eyebrow">Vault</div>
        <h1 className="font-display mt-1 text-[30px] font-semibold tracking-tight text-bone">
          Sovereign secret store
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-bone-2">
          AES-256 at rest, TLS in transit, runtime injection only - secrets never appear in logs.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Badge tone="ok" dot>
            live · <span className="font-mono">/api/v1/auth/api-keys</span>
          </Badge>
          <Badge tone="primary">
            <Lock className="h-3 w-3" /> AES-256
          </Badge>
          <Badge tone="info">workspace scoped</Badge>
          <Badge tone="muted">
            {active} active · {revoked} revoked
          </Badge>
          {expiring > 0 && (
            <Badge tone="warn" dot>
              {expiring} expiring
            </Badge>
          )}
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        <button
          className="v-btn-ghost h-8 cursor-not-allowed px-3 text-xs opacity-70"
          disabled
          title="Bulk rotation is not exposed by the live backend yet."
        >
          <RotateCcw className="h-3.5 w-3.5" /> Rotate all
        </button>
        <button className="v-btn-primary h-8 px-3 text-xs" onClick={onNew}>
          <Plus className="h-3.5 w-3.5" /> New secret
        </button>
      </div>
    </header>
  );
}

function SecretsTable({
  keys,
  loading,
  query,
  onQuery,
  active,
  revoked,
  expiring,
  revokePending,
  onInspect,
  onRevoke,
}: {
  keys: ApiKey[];
  loading: boolean;
  query: string;
  onQuery: (value: string) => void;
  active: number;
  revoked: number;
  expiring: number;
  revokePending: boolean;
  onInspect: (key: ApiKey) => void;
  onRevoke: (key: ApiKey) => void;
}) {
  return (
    <div className="frame overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-rule/80 px-4 py-3">
        <label className="flex w-full max-w-[360px] items-center gap-2 rounded-md border border-rule bg-ink-1/70 px-2.5 py-1.5">
          <Search className="h-4 w-4 text-muted" />
          <input
            className="w-full bg-transparent text-[13px] text-bone outline-none placeholder:text-muted"
            placeholder="Search by name, scope, or prefix..."
            value={query}
            onChange={(event) => onQuery(event.target.value)}
          />
        </label>
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="muted">{active} active</Badge>
          <Badge tone={expiring ? "warn" : "muted"} dot={expiring > 0}>
            {expiring} expiring
          </Badge>
          <Badge tone="muted">{revoked} revoked</Badge>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[840px] text-[12.5px]">
          <thead className="border-b border-rule/70 bg-ink-1/70 text-eyebrow">
            <tr>
              <th className="px-4 py-2 text-left">Name</th>
              <th className="px-4 py-2 text-left">Type</th>
              <th className="px-4 py-2 text-left">Scope</th>
              <th className="px-4 py-2 text-left">Last used</th>
              <th className="px-4 py-2 text-left">Rotation</th>
              <th className="px-4 py-2 text-left">Status</th>
              <th className="px-4 py-2 text-right" />
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={7} className="px-5 py-8 text-center font-mono text-[12px] text-muted">
                  loading...
                </td>
              </tr>
            )}
            {!loading && keys.length === 0 && (
              <tr>
                <td colSpan={7} className="px-5 py-8 text-center font-mono text-[12px] text-muted">
                  No keys match this view.
                </td>
              </tr>
            )}
            {keys.map((key) => (
              <tr key={key.id} className="border-b border-rule/50 last:border-0 hover-elevate">
                <td className="px-4 py-2 font-mono text-bone">
                  <div>{key.name}</div>
                  <div className="text-[11px] text-muted">{key.key_prefix}...</div>
                </td>
                <td className="px-4 py-2 text-muted">API key</td>
                <td className="px-4 py-2">
                  <div className="flex flex-wrap gap-1">
                    {key.scopes.map((scope) => (
                      <Badge key={scope} tone="muted">
                        {scope}
                      </Badge>
                    ))}
                  </div>
                </td>
                <td className="px-4 py-2 text-muted">{key.last_used_at ? relativeTime(key.last_used_at) : "never"}</td>
                <td className="px-4 py-2 font-mono text-[11.5px] text-bone-2">
                  <Clock3 className="mr-1 inline h-3 w-3 text-muted" />
                  {rotationLabel(key)}
                </td>
                <td className="px-4 py-2">
                  <Badge tone={key.is_active ? (isExpiring(key) ? "warn" : "ok") : "warn"} dot>
                    {key.is_active ? (isExpiring(key) ? "expiring" : "active") : "revoked"}
                  </Badge>
                </td>
                <td className="px-4 py-2 text-right">
                  <button className="v-btn-ghost h-7 px-2" title="Inspect key metadata" onClick={() => onInspect(key)}>
                    <MoreHorizontal className="h-3.5 w-3.5" />
                  </button>
                  {key.is_active && (
                    <button
                      className="v-btn-ghost ml-1 h-7 px-2 text-crimson hover:bg-crimson/10"
                      onClick={() => onRevoke(key)}
                      disabled={revokePending}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ApiKeysPanel({ keys }: { keys: ApiKey[] }) {
  return (
    <div className="frame col-span-12 p-4 lg:col-span-7">
      <div className="text-eyebrow">API keys</div>
      <div className="font-display text-[14px] text-bone">Tenant-scoped · per-resource permissions</div>
      <div className="mt-3 space-y-2">
        {keys.length === 0 && (
          <div className="rounded-md border border-dashed border-rule bg-ink-1/40 px-4 py-5 text-sm text-bone-2">
            No visible keys. Issue one to call governed execution APIs.
          </div>
        )}
        {keys.map((key) => (
          <div key={key.id} className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-rule bg-ink-1/45 px-3 py-2.5">
            <div className="flex items-start gap-3">
              <div className="grid h-8 w-8 place-items-center rounded-md bg-brass/15 text-brass-2">
                <KeyRound className="h-4 w-4" />
              </div>
              <div>
                <div className="text-[13px] text-bone">{key.name}</div>
                <div className="font-mono text-[11px] text-muted">{key.key_prefix}...</div>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {key.scopes.map((scope) => (
                <Badge key={scope} tone="muted">
                  {scope}
                </Badge>
              ))}
              <Badge tone={key.is_active ? "ok" : "warn"} dot>
                {key.is_active ? "active" : "revoked"}
              </Badge>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function VaultPosture({
  active,
  revoked,
  expiring,
  total,
}: {
  active: number;
  revoked: number;
  expiring: number;
  total: number;
}) {
  const rows = [
    { label: "Runtime injection only", value: "X-API-Key / Bearer path" },
    { label: "One-shot reveal", value: "raw key shown once" },
    { label: "Per-key rate limits", value: `${active} active configured` },
    { label: "Revocation", value: `${revoked} revoked` },
    { label: "Expiration posture", value: expiring ? `${expiring} expiring within 30d` : "no 30d expiries" },
    { label: "Vault inventory", value: `${total} total keys` },
  ];
  return (
    <div className="frame col-span-12 p-4 lg:col-span-5">
      <div className="text-eyebrow">Vault posture</div>
      <div className="font-display text-[14px] text-bone">Governance over storage</div>
      <ul className="mt-3 space-y-2 text-[12px]">
        {rows.map((row) => (
          <li key={row.label} className="flex items-center justify-between gap-3 rounded-md border border-rule bg-ink-1/45 px-3 py-2">
            <span className="flex items-center gap-2 text-bone-2">
              <CheckCircle2 className="h-3.5 w-3.5 text-moss" />
              {row.label}
            </span>
            <span className="text-right font-mono text-[11px] text-muted">{row.value}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function KeyDetailDrawer({ item, onClose }: { item: ApiKey; onClose: () => void }) {
  const rows = [
    ["Prefix", `${item.key_prefix}...`],
    ["Status", item.is_active ? "active" : "revoked"],
    ["Scopes", item.scopes.join(", ") || "none"],
    ["Rate limit", `${item.rate_limit_per_minute} / min`],
    ["Created", relativeTime(item.created_at)],
    ["Last used", item.last_used_at ? relativeTime(item.last_used_at) : "never"],
    ["Expires", item.expires_at ? rotationLabel(item) : "manual rotation"],
  ];

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/50 backdrop-blur-sm" role="dialog" aria-modal="true">
      <button className="absolute inset-0 cursor-default" onClick={onClose} aria-label="Close key details" />
      <aside className="frame relative h-full w-full max-w-md overflow-y-auto rounded-none border-y-0 border-r-0 p-5 shadow-2xl">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-eyebrow">Vault key detail</div>
            <h2 className="font-display mt-1 text-xl font-semibold text-bone">{item.name}</h2>
            <p className="mt-1 text-sm text-bone-2">
              Metadata only. Raw secrets are shown once at issue time and are never recoverable from the vault.
            </p>
          </div>
          <button onClick={onClose} className="rounded p-1 text-muted hover:bg-white/5 hover:text-bone" aria-label="Close">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mt-5 space-y-2">
          {rows.map(([label, value]) => (
            <div key={label} className="flex items-center justify-between gap-3 rounded-md border border-rule bg-ink-1/45 px-3 py-2 text-[12px]">
              <span className="text-muted">{label}</span>
              <span className="max-w-[60%] truncate text-right font-mono text-bone">{value}</span>
            </div>
          ))}
        </div>

        <div className="mt-5 rounded-md border border-brass/30 bg-brass/5 p-3 text-[12px] text-bone-2">
          <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.12em] text-brass-2">Operational rule</div>
          Rotate by issuing a replacement key, updating the integration, then revoking this key. Bulk rotation remains
          disabled until the backend exposes a safe batch-rotation route.
        </div>
      </aside>
    </div>
  );
}

function JustCreatedBanner({ item, onDismiss }: { item: ApiKeyCreateResponse; onDismiss: () => void }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(item.raw_key).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };
  return (
    <div className="frame mb-4 border-brass/50 bg-brass/5 p-5">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.12em] text-brass-2">
          <KeyRound className="h-3 w-3" />
          Secret issued - copy now, it will never be shown again
        </div>
        <button onClick={onDismiss} className="rounded p-1 text-muted hover:bg-white/5 hover:text-bone" aria-label="Dismiss">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="mt-2 flex items-center gap-2 rounded-md border border-rule bg-ink-2 px-3 py-2">
        <code className="flex-1 break-all font-mono text-[12px] text-bone">{item.raw_key}</code>
        <button className={cn("v-btn-ghost shrink-0", copied && "text-moss")} onClick={copy}>
          {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <div className="mt-2 font-mono text-[11px] text-muted">
        Key <span className="text-bone">{item.name}</span> · prefix <span className="text-bone">{item.key_prefix}...</span> · scopes{" "}
        {item.scopes.join(", ")}
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

  const toggleScope = (scope: string) => {
    setScopes((prev) => (prev.includes(scope) ? prev.filter((x) => x !== scope) : [...prev, scope]));
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
      <div className="frame relative w-full max-w-md p-5 shadow-2xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-display text-lg font-semibold text-bone">Issue API key</h2>
          <button onClick={onClose} className="rounded p-1 text-muted hover:bg-white/5 hover:text-bone" aria-label="Close">
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
              placeholder="production-backend"
              value={name}
              onChange={(event) => setName(event.target.value)}
              autoFocus
            />
          </div>

          <div>
            <div className="v-label">Scopes</div>
            <div className="flex flex-wrap gap-2">
              {AVAILABLE_SCOPES.map((scope) => {
                const on = scopes.includes(scope);
                return (
                  <button
                    key={scope}
                    onClick={() => toggleScope(scope)}
                    className={cn(
                      "rounded-md border px-3 py-1 font-mono text-[12px] transition",
                      on ? "border-brass/50 bg-brass/15 text-brass-2" : "border-rule bg-white/[0.02] text-muted hover:text-bone",
                    )}
                  >
                    {scope}
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
                onChange={(event) => setRate(parseInt(event.target.value || "60", 10))}
              />
            </div>
            <div>
              <label className="v-label" htmlFor="expiry">
                Expires
              </label>
              <select id="expiry" className="v-input" value={expiry} onChange={(event) => setExpiry(event.target.value)}>
                <option value="30">30 days</option>
                <option value="90">90 days</option>
                <option value="365">1 year</option>
                <option value="never">Never</option>
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
            <button className="v-btn-primary flex-1" onClick={submit} disabled={pending || !name.trim() || scopes.length === 0}>
              {pending && <Loader2 className="h-4 w-4 animate-spin" />}
              {pending ? "Issuing..." : "Issue key"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function filterKeys(keys: ApiKey[], query: string): ApiKey[] {
  const q = query.trim().toLowerCase();
  if (!q) return keys;
  return keys.filter((key) =>
    [key.name, key.key_prefix, key.scopes.join(" ")]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(q)),
  );
}

function daysUntil(iso: string): number {
  const target = new Date(iso).getTime();
  if (!Number.isFinite(target)) return Number.POSITIVE_INFINITY;
  return Math.ceil((target - Date.now()) / 86400000);
}

function isExpiring(key: ApiKey): boolean {
  return Boolean(key.expires_at && daysUntil(key.expires_at) <= 30 && key.is_active);
}

function rotationLabel(key: ApiKey): string {
  if (!key.expires_at) return "manual";
  const days = daysUntil(key.expires_at);
  if (days < 0) return "expired";
  if (days === 0) return "today";
  return `${days} d`;
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
