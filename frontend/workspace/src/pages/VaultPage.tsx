import { useState, useEffect, useCallback } from "react";
import { Plus, Search, RotateCcw, Eye, RefreshCw, Shield, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

interface Secret {
  name: string;
  type: string;
  scope: string;
  lastUsed: string;
  rotation: string;
  status: "Active" | "Rotating" | "Expiring";
}

interface ApiKeyItem {
  name: string;
  prefix: string;
  scopes: string[];
  status: "Active" | "Rotating";
}

const STATIC_SECRETS: Secret[] = [
  { name: "OPENAI_KEY_PROXY", type: "API key", scope: "Deployments:Read", lastUsed: "2 min", rotation: "30 d", status: "Active" },
  { name: "POSTGRES_RAG", type: "Database URI", scope: "Pipelines:RAG-Only", lastUsed: "12 min", rotation: "manual", status: "Active" },
  { name: "STRIPE_LIVE", type: "API key", scope: "Billing:Read", lastUsed: "1 hr", rotation: "60 d", status: "Active" },
  { name: "AWS_ASSUME_ROLE", type: "OAuth token", scope: "Burst:Assume", lastUsed: "now", rotation: "30 d", status: "Active" },
  { name: "GH_PR_BOT", type: "OAuth token", scope: "CI:Test-Runner", lastUsed: "5 hr", rotation: "rotating", status: "Rotating" },
  { name: "TLS_CHAIN_INTERNAL", type: "Certificate", scope: "mTLS", lastUsed: "—", rotation: "365 d", status: "Expiring" },
];

const STATIC_API_KEYS: ApiKeyItem[] = [
  { name: "production-chat", prefix: "vk_live_8h2x_", scopes: ["Chat:Write", "Embeddings:Read"], status: "Active" },
  { name: "rag-ingest", prefix: "vk_live_d0in_", scopes: ["Embeddings:Write", "Pipelines:Invoke"], status: "Active" },
  { name: "ci-test-runner", prefix: "vk_test_42as_", scopes: ["Chat:Write", "Completions:Write"], status: "Rotating" },
];

const VAULT_POSTURE = [
  { label: "Runtime injection only", value: "100% pipelines compliant" },
  { label: "Egress allowlist", value: "12 hosts · 0 pending" },
  { label: "Auto-rotation", value: "21 / 28 secrets" },
  { label: "Per-secret access logs", value: "tamper-evident" },
  { label: "HSM seal", value: "FIPS 140-2 L3" },
];

const STATUS_COLORS: Record<string, string> = {
  Active: "bg-moss/20 text-moss",
  Rotating: "bg-amber/20 text-amber",
  Expiring: "bg-crimson/20 text-crimson",
};

export function VaultPage() {
  const [secrets] = useState<Secret[]>(STATIC_SECRETS);
  const [apiKeys] = useState<ApiKeyItem[]>(STATIC_API_KEYS);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      await api.get("/auth/api-keys");
    } catch { /* use static */ }
    setLoading(false);
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <p className="v-section-label">Vault</p>
          <h1 className="mt-1 text-2xl font-bold text-bone">Sovereign secret store</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted">
            AES-256 at rest, TLS in transit, runtime injection only — secrets never appear in env vars or logs.
          </p>
          <div className="mt-3 flex items-center gap-2">
            <span className="rounded bg-amber/15 px-2 py-0.5 font-mono text-[9px] font-semibold text-amber">AES-256-GCM</span>
            <span className="rounded bg-electric/15 px-2 py-0.5 font-mono text-[9px] font-semibold text-electric">Sealed by HSM</span>
            <span className="font-mono text-[10px] text-muted">{secrets.length} Secrets · 8 Certificates</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-1.5 rounded-md border border-rule px-3 py-1.5 text-xs text-muted hover:text-bone hover:border-muted transition-colors">
            <RotateCcw className="h-3.5 w-3.5" /> Rotate all
          </button>
          <button className="v-btn-primary text-xs"><Plus className="h-3.5 w-3.5" /> New secret</button>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
        <input type="text" placeholder="Search by name, scope, or type..." className="v-input pl-10 w-full max-w-md" />
        <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
          <span className="font-mono text-[10px] text-muted">{secrets.length} Secrets</span>
          <span className="rounded bg-crimson/15 px-1.5 py-0.5 font-mono text-[9px] text-crimson">1 Expiring</span>
        </div>
      </div>

      {/* Secrets table */}
      <div className="v-card-flush">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-rule text-left">
              <th className="px-4 py-2.5 font-mono text-[9px] uppercase text-muted">Name</th>
              <th className="px-3 py-2.5 font-mono text-[9px] uppercase text-muted">Type</th>
              <th className="px-3 py-2.5 font-mono text-[9px] uppercase text-muted">Scope</th>
              <th className="px-3 py-2.5 font-mono text-[9px] uppercase text-muted">Last Used</th>
              <th className="px-3 py-2.5 font-mono text-[9px] uppercase text-muted">Rotation</th>
              <th className="px-3 py-2.5 font-mono text-[9px] uppercase text-muted">Status</th>
              <th className="w-20"></th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="px-4 py-6 text-center text-muted"><Loader2 className="mx-auto h-4 w-4 animate-spin" /></td></tr>
            ) : secrets.map((s) => (
              <tr key={s.name} className="border-b border-rule/40 hover:bg-white/[0.02]">
                <td className="px-4 py-2.5">
                  <span className="font-mono font-semibold text-bone">{s.name}</span>
                </td>
                <td className="px-3 py-2.5 text-muted">{s.type}</td>
                <td className="px-3 py-2.5">
                  <span className="font-mono text-[10px] text-muted">{s.scope}</span>
                </td>
                <td className="px-3 py-2.5 text-muted">{s.lastUsed}</td>
                <td className="px-3 py-2.5">
                  <span className="inline-flex items-center gap-1 font-mono text-[10px] text-muted">
                    <RefreshCw className="h-2.5 w-2.5" /> {s.rotation}
                  </span>
                </td>
                <td className="px-3 py-2.5">
                  <span className={`rounded px-1.5 py-0.5 text-[9px] font-mono font-semibold ${STATUS_COLORS[s.status]}`}>
                    {s.status}
                  </span>
                </td>
                <td className="px-3 py-2.5">
                  <div className="flex gap-1.5">
                    <Eye className="h-3 w-3 text-muted/50 hover:text-bone cursor-pointer" />
                    <RotateCcw className="h-3 w-3 text-muted/50 hover:text-bone cursor-pointer" />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* API Keys + Vault Posture */}
      <div className="grid gap-4 lg:grid-cols-5">
        {/* API Keys */}
        <div className="v-card lg:col-span-3">
          <p className="v-section-label">API Keys</p>
          <p className="mt-0.5 text-sm font-semibold text-bone">Tenant-scoped · per-resource permissions</p>
          <div className="mt-4 space-y-3">
            {apiKeys.map((k) => (
              <div key={k.name} className="flex items-center gap-4 rounded-md border border-rule/40 bg-ink-3/30 px-4 py-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-md bg-ink-2 border border-rule">
                  <Shield className="h-4 w-4 text-brass" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-bone text-xs">{k.name}</span>
                    <span className="font-mono text-[9px] text-muted">{k.prefix}</span>
                  </div>
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    {k.scopes.map((scope) => (
                      <span key={scope} className="rounded bg-ink-2 px-1.5 py-0.5 font-mono text-[8px] text-muted">{scope}</span>
                    ))}
                  </div>
                </div>
                <span className={`rounded px-1.5 py-0.5 text-[9px] font-mono font-semibold ${STATUS_COLORS[k.status]}`}>
                  {k.status}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Vault Posture */}
        <div className="v-card lg:col-span-2">
          <p className="v-section-label">Vault Posture</p>
          <p className="mt-0.5 text-sm font-semibold text-bone">Governance over storage</p>
          <div className="mt-4 space-y-3">
            {VAULT_POSTURE.map((item) => (
              <div key={item.label} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-moss" />
                  <span className="text-xs text-bone">{item.label}</span>
                </div>
                <span className="font-mono text-[10px] text-muted">{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
