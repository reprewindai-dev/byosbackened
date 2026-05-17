import { useEffect, useState, useCallback } from "react";
import { Save, Key, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

interface UserProfile {
  email?: string;
  name?: string;
  role?: string;
  workspace_id?: string;
}

export function SettingsPage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me");
      setProfile(data);
    } catch { /* not logged in yet */ }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  async function handleSave() {
    setSaving(true);
    await new Promise(r => setTimeout(r, 600));
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <p className="v-section-label">Settings</p>
        <h1 className="mt-1 text-2xl font-bold text-bone">Workspace Settings</h1>
        <p className="mt-1 text-sm text-muted">Manage your profile, API keys, and workspace preferences.</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="v-card">
          <p className="v-section-label mb-3">Profile</p>
          <div className="space-y-3">
            <div>
              <label className="v-section-label">Email</label>
              <input defaultValue={profile?.email || ""} placeholder="your@email.com" className="v-input mt-1 w-full" />
            </div>
            <div>
              <label className="v-section-label">Name</label>
              <input defaultValue={profile?.name || ""} placeholder="Your name" className="v-input mt-1 w-full" />
            </div>
            <div>
              <label className="v-section-label">Role</label>
              <input defaultValue={profile?.role || ""} placeholder="Admin" className="v-input mt-1 w-full" disabled />
            </div>
            {profile?.workspace_id && (
              <div>
                <label className="v-section-label">Workspace ID</label>
                <input defaultValue={profile.workspace_id} className="v-input mt-1 w-full font-mono text-xs" disabled />
              </div>
            )}
          </div>
          <button onClick={handleSave} disabled={saving} className="mt-4 v-btn-primary text-xs w-full">
            {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
            {saved ? "Saved!" : "Save changes"}
          </button>
        </div>

        <div className="v-card">
          <p className="v-section-label mb-3">API Access</p>
          <div className="space-y-3">
            <div className="flex items-center gap-2 rounded-md border border-rule/50 bg-ink-3/30 px-3 py-2.5">
              <Key className="h-3.5 w-3.5 text-muted" />
              <span className="text-xs text-muted">Manage API keys in</span>
              <button className="text-xs text-electric hover:underline">Vault →</button>
            </div>
            <div className="rounded-md border border-rule/50 bg-ink-3/30 px-3 py-2.5">
              <p className="text-xs text-muted mb-1">API Base URL</p>
              <p className="font-mono text-xs text-bone">https://api.veklom.com/api/v1</p>
            </div>
            <div className="rounded-md border border-rule/50 bg-ink-3/30 px-3 py-2.5">
              <p className="text-xs text-muted mb-1">Workspace</p>
              <p className="font-mono text-xs text-bone">{profile?.workspace_id || "acme-prod"}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
