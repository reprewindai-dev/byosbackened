import { useState, useEffect, useCallback } from "react";
import { Save, Key, Bell, Shield, Globe, Loader2 } from "lucide-react";
import { useAuthStore } from "@/store/auth-store";
import { api } from "@/lib/api";

interface ApiKeyEntry {
  id: string;
  key_name?: string;
  prefix?: string;
  is_active?: boolean;
}

export function SettingsPage() {
  const user = useAuthStore((s) => s.user);
  const workspaceName = user?.workspace_name || "workspace";
  const workspaceSlug = user?.workspace_slug || "—";
  const [apiKeys, setApiKeys] = useState<ApiKeyEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [wsName, setWsName] = useState(workspaceName);

  const fetchData = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/api-keys");
      setApiKeys(Array.isArray(data) ? data.slice(0, 4) : (data?.keys || []).slice(0, 4));
    } catch { /* 403 or not available */ }
    setLoading(false);
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);
  useEffect(() => { setWsName(workspaceName); }, [workspaceName]);

  async function saveGeneral() {
    setSaving(true);
    try {
      await api.patch("/workspace/settings", { workspace_name: wsName });
    } catch { /* ignore — endpoint may not exist yet */ }
    setSaving(false);
  }

  async function setupMfa() {
    try {
      const { data } = await api.post("/auth/mfa/setup");
      if (data?.qr_uri) alert(`Scan this QR URI in your authenticator app:\n\n${data.qr_uri}`);
    } catch { /* handled */ }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <p className="v-section-label">Settings</p>
        <h1 className="mt-1 text-2xl font-bold text-bone">Workspace configuration</h1>
        <p className="mt-1 text-sm text-muted">API keys, notifications, security, and region settings.</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="v-card">
          <p className="v-section-label">General</p>
          <div className="mt-4 space-y-3">
            <div>
              <label className="v-label">Workspace name</label>
              <input className="v-input" value={wsName} onChange={(e) => setWsName(e.target.value)} />
            </div>
            <div>
              <label className="v-label">Slug</label>
              <input className="v-input" defaultValue={workspaceSlug} readOnly />
            </div>
            <div>
              <label className="v-label">Industry</label>
              <input className="v-input" defaultValue={user?.industry || "—"} readOnly />
            </div>
            <div>
              <label className="v-label">License Tier</label>
              <input className="v-input" defaultValue={user?.license_tier || "—"} readOnly />
            </div>
            <button onClick={saveGeneral} disabled={saving} className="v-btn-primary text-xs">
              {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />} Save changes
            </button>
          </div>
        </div>

        <div className="v-card">
          <p className="v-section-label">API Keys</p>
          <div className="mt-4 space-y-3">
            {loading ? (
              <div className="py-4 text-center"><Loader2 className="mx-auto h-4 w-4 animate-spin text-muted" /></div>
            ) : apiKeys.length > 0 ? apiKeys.map((k) => (
              <div key={k.id} className="flex items-center justify-between rounded-md border border-rule bg-ink-3 px-3 py-2.5">
                <div>
                  <p className="text-xs text-bone">{k.key_name || "API key"}</p>
                  <p className="font-mono text-[10px] text-muted">{k.prefix || "—"}...</p>
                </div>
                <div className="flex gap-1">
                  <span className={`v-badge ${k.is_active !== false ? "v-badge-green" : "v-badge-muted"}`}>{k.is_active !== false ? "active" : "revoked"}</span>
                  <button className="v-btn-ghost px-1.5 py-1"><Key className="h-3 w-3" /></button>
                </div>
              </div>
            )) : (
              <p className="text-xs text-muted py-2">No API keys — create one in the Vault page</p>
            )}
          </div>
        </div>

        <div className="v-card">
          <p className="v-section-label">Notifications</p>
          <div className="mt-4 space-y-3">
            {["Cost alerts", "Security events", "Compliance reports", "Team activity"].map((n) => (
              <div key={n} className="flex items-center justify-between py-1.5">
                <span className="text-xs text-bone">{n}</span>
                <div className="h-5 w-9 rounded-full bg-moss/30 border border-moss/50 relative cursor-pointer">
                  <div className="absolute left-[18px] top-[2px] h-3.5 w-3.5 rounded-full bg-moss transition-all" />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="v-card">
          <p className="v-section-label">Security</p>
          <div className="mt-4 space-y-3">
            <div className="flex items-center justify-between py-1.5">
              <div>
                <p className="text-xs text-bone">MFA</p>
                <p className="text-[10px] text-muted">{user?.mfa_enabled ? "MFA is enabled on your account" : "Enable 2FA for your account"}</p>
              </div>
              {user?.mfa_enabled ? (
                <span className="v-badge v-badge-green">enabled</span>
              ) : (
                <button onClick={setupMfa} className="v-btn-primary text-[10px] px-2 py-1">Enable MFA</button>
              )}
            </div>
            <div className="flex items-center justify-between py-1.5">
              <div>
                <p className="text-xs text-bone">GitHub Connected</p>
                <p className="text-[10px] text-muted">{user?.github_username || "Not connected"}</p>
              </div>
              <span className={`v-badge ${user?.github_connected ? "v-badge-green" : "v-badge-muted"}`}>{user?.github_connected ? "connected" : "off"}</span>
            </div>
            <div className="flex items-center justify-between py-1.5">
              <div>
                <p className="text-xs text-bone">Account ID</p>
                <p className="font-mono text-[10px] text-muted">{user?.id || "—"}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
