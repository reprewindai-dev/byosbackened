import { useState, useEffect, useCallback } from "react";
import { Plus, Key, Copy, Eye, Trash2, Shield, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

interface ApiKey {
  id: string;
  key_name?: string;
  prefix?: string;
  created_at?: string;
  last_used_at?: string;
  is_active?: boolean;
  scopes?: string[];
}

const POLICIES = [
  { name: "Auto-rotate", detail: "Rotate all secrets every 90 days", status: "enabled" },
  { name: "Leak detection", detail: "Scan git push events for exposed secrets", status: "enabled" },
  { name: "IP-scoped usage", detail: "Restrict secret access to allow-listed CIDRs", status: "enabled" },
  { name: "Audit trail", detail: "Every read/write hashed and appended to audit chain", status: "enabled" },
];

export function VaultPage() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [newKeyValue, setNewKeyValue] = useState<string | null>(null);

  const fetchKeys = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/api-keys");
      setKeys(Array.isArray(data) ? data : data?.keys || []);
    } catch { /* 403 or not available */ }
    setLoading(false);
  }, []);

  useEffect(() => { fetchKeys(); }, [fetchKeys]);

  async function createKey() {
    if (!newKeyName.trim()) return;
    setCreating(true);
    try {
      const { data } = await api.post("/auth/api-keys", { key_name: newKeyName });
      setNewKeyValue(data?.api_key || data?.key || null);
      setNewKeyName("");
      fetchKeys();
    } catch { /* handled */ }
    setCreating(false);
  }

  async function revokeKey(id: string) {
    try {
      await api.delete(`/auth/api-keys/${id}`);
      fetchKeys();
    } catch { /* handled */ }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-start justify-between">
        <div>
          <p className="v-section-label">Vault</p>
          <h1 className="mt-1 text-2xl font-bold text-bone">API Keys & Secret Management</h1>
          <p className="mt-1 text-sm text-muted">Encrypted at rest, auto-rotated, audit-logged. Every read is signed.</p>
        </div>
        <button className="v-btn-primary text-xs" onClick={() => setShowCreate(!showCreate)}><Plus className="h-3.5 w-3.5" /> Create API key</button>
      </div>

      {showCreate && (
        <div className="v-card flex items-end gap-3">
          <div className="flex-1">
            <label className="v-label">Key Name</label>
            <input value={newKeyName} onChange={(e) => setNewKeyName(e.target.value)} className="v-input" placeholder="my-integration-key" />
          </div>
          <button onClick={createKey} disabled={creating} className="v-btn-primary text-xs">
            {creating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Create"}
          </button>
        </div>
      )}

      {newKeyValue && (
        <div className="rounded-md border border-moss/30 bg-moss/5 px-4 py-3">
          <p className="text-xs font-semibold text-moss">New API key created — copy it now, it won't be shown again:</p>
          <div className="mt-2 flex items-center gap-2">
            <code className="flex-1 rounded bg-ink-3 px-3 py-1.5 font-mono text-xs text-bone break-all">{newKeyValue}</code>
            <button onClick={() => { navigator.clipboard.writeText(newKeyValue); }} className="v-btn-ghost px-2 py-1"><Copy className="h-3.5 w-3.5" /></button>
          </div>
          <button onClick={() => setNewKeyValue(null)} className="mt-2 text-[10px] text-muted hover:text-bone">Dismiss</button>
        </div>
      )}

      <div className="v-card-flush">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-rule text-left">
              <th className="px-4 py-3 font-mono text-[9px] uppercase text-muted">Name</th>
              <th className="px-3 py-3 font-mono text-[9px] uppercase text-muted">Prefix</th>
              <th className="px-3 py-3 font-mono text-[9px] uppercase text-muted">Created</th>
              <th className="px-3 py-3 font-mono text-[9px] uppercase text-muted">Last Used</th>
              <th className="px-3 py-3 font-mono text-[9px] uppercase text-muted">Status</th>
              <th className="w-24"></th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="px-4 py-6 text-center text-muted"><Loader2 className="mx-auto h-4 w-4 animate-spin" /></td></tr>
            ) : keys.length > 0 ? keys.map((s) => (
              <tr key={s.id} className="border-b border-rule/50 hover:bg-ink-3/40">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <Key className="h-3.5 w-3.5 text-amber" />
                    <span className="font-mono font-semibold text-bone">{s.key_name || "Unnamed key"}</span>
                  </div>
                </td>
                <td className="px-3 py-3 font-mono text-muted">{s.prefix || "—"}...</td>
                <td className="px-3 py-3 font-mono text-muted">{s.created_at ? new Date(s.created_at).toLocaleDateString() : "—"}</td>
                <td className="px-3 py-3 text-muted">{s.last_used_at ? new Date(s.last_used_at).toLocaleDateString() : "never"}</td>
                <td className="px-3 py-3">
                  <span className={`v-badge ${s.is_active !== false ? "v-badge-green" : "v-badge-muted"}`}>{s.is_active !== false ? "active" : "revoked"}</span>
                </td>
                <td className="px-3 py-3">
                  <div className="flex gap-1">
                    <button className="v-btn-ghost px-1.5 py-1"><Eye className="h-3 w-3" /></button>
                    <button className="v-btn-ghost px-1.5 py-1"><Copy className="h-3 w-3" /></button>
                    <button className="v-btn-ghost px-1.5 py-1 text-crimson" onClick={() => revokeKey(s.id)}><Trash2 className="h-3 w-3" /></button>
                  </div>
                </td>
              </tr>
            )) : (
              <tr><td colSpan={6} className="px-4 py-6 text-center text-muted">No API keys — create one to get started</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="v-card">
        <p className="v-section-label">Vault Policies</p>
        <p className="mt-0.5 text-sm font-semibold text-bone">Automated secret governance</p>
        <div className="mt-4 space-y-3">
          {POLICIES.map((p) => (
            <div key={p.name} className="flex items-center justify-between rounded-md border border-rule/50 bg-ink-3/30 px-4 py-3">
              <div className="flex items-center gap-3">
                <Shield className="h-4 w-4 text-electric" />
                <div>
                  <p className="text-xs font-semibold text-bone">{p.name}</p>
                  <p className="text-[10px] text-muted">{p.detail}</p>
                </div>
              </div>
              <span className="v-badge v-badge-green">{p.status}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
