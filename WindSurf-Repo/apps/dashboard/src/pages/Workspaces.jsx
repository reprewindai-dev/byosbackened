import React, { useState, useEffect, useCallback } from 'react';
import { workspacesApi } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import PageHeader from '../components/PageHeader';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';

export default function Workspaces() {
  const { user } = useAuth();
  const [workspace, setWorkspace] = useState(null);
  const [secrets, setSecrets] = useState([]);
  const [retention, setRetention] = useState(null);
  const [loading, setLoading] = useState(true);
  const [addingSecret, setAddingSecret] = useState(false);
  const [secretForm, setSecretForm] = useState({ key: '', value: '', description: '' });
  const [secretMsg, setSecretMsg] = useState('');
  const [showSecretForm, setShowSecretForm] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [wsRes, secretsRes, retRes] = await Promise.all([
        workspacesApi.getCurrent().catch(() => ({ data: null })),
        workspacesApi.listSecrets().catch(() => ({ data: { secrets: [] } })),
        workspacesApi.getRetentionPolicy().catch(() => ({ data: null })),
      ]);
      setWorkspace(wsRes.data);
      setSecrets(secretsRes.data.secrets || secretsRes.data || []);
      setRetention(retRes.data);
    } catch { /* silent */ } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleAddSecret = async (e) => {
    e.preventDefault();
    if (!secretForm.key || !secretForm.value) {
      setSecretMsg('Key and value are required');
      return;
    }
    setAddingSecret(true);
    setSecretMsg('');
    try {
      await workspacesApi.createSecret(secretForm);
      setSecretForm({ key: '', value: '', description: '' });
      setShowSecretForm(false);
      setSecretMsg('Secret saved');
      await load();
    } catch (err) {
      setSecretMsg(err.response?.data?.detail || 'Failed to save secret');
    } finally {
      setAddingSecret(false);
      setTimeout(() => setSecretMsg(''), 3000);
    }
  };

  const handleDeleteSecret = async (key) => {
    if (!window.confirm(`Delete secret "${key}"?`)) return;
    try {
      await workspacesApi.deleteSecret(key);
      await load();
    } catch (err) {
      alert(err.response?.data?.detail || 'Delete failed');
    }
  };

  if (loading) return <LoadingSpinner centered />;

  return (
    <div className="space-y-6 max-w-4xl">
      <PageHeader
        title="Workspace"
        description="Manage your workspace configuration, secrets, and retention policies"
      />

      {/* Workspace info */}
      <div className="card">
        <h2 className="text-sm font-semibold text-white mb-4">Workspace Info</h2>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-xs text-gray-500 mb-0.5">Name</div>
            <div className="text-gray-200">{workspace?.name || 'N/A'}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500 mb-0.5">Slug</div>
            <div className="text-gray-200 font-mono text-xs">{workspace?.slug || 'N/A'}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500 mb-0.5">Workspace ID</div>
            <div className="text-gray-400 font-mono text-xs">{user?.workspace_id || 'N/A'}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500 mb-0.5">Status</div>
            <div className={workspace?.is_active ? 'text-emerald-400' : 'text-red-400'}>
              {workspace?.is_active ? '● Active' : '● Inactive'}
            </div>
          </div>
          {workspace?.created_at && (
            <div>
              <div className="text-xs text-gray-500 mb-0.5">Created</div>
              <div className="text-gray-400 text-xs">{new Date(workspace.created_at).toLocaleDateString()}</div>
            </div>
          )}
        </div>
      </div>

      {/* Secrets */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-white">Workspace Secrets</h2>
          <button onClick={() => setShowSecretForm((p) => !p)} className="btn-primary text-xs">
            {showSecretForm ? '✕ Cancel' : '+ Add Secret'}
          </button>
        </div>

        {secretMsg && (
          <div className={`mb-3 text-xs ${secretMsg.includes('saved') ? 'text-emerald-400' : 'text-red-400'}`}>{secretMsg}</div>
        )}

        {showSecretForm && (
          <form onSubmit={handleAddSecret} className="mb-4 p-4 bg-gray-800/40 rounded-lg space-y-3">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
              <div>
                <label className="label">Key</label>
                <input type="text" className="input" placeholder="e.g. OPENAI_API_KEY"
                  value={secretForm.key} onChange={(e) => setSecretForm((f) => ({ ...f, key: e.target.value }))} required />
              </div>
              <div>
                <label className="label">Value</label>
                <input type="password" className="input" placeholder="Secret value"
                  value={secretForm.value} onChange={(e) => setSecretForm((f) => ({ ...f, value: e.target.value }))} required />
              </div>
              <div>
                <label className="label">Description</label>
                <input type="text" className="input" placeholder="What is this for?"
                  value={secretForm.description} onChange={(e) => setSecretForm((f) => ({ ...f, description: e.target.value }))} />
              </div>
            </div>
            <button type="submit" className="btn-primary text-xs" disabled={addingSecret}>
              {addingSecret ? 'Saving…' : 'Save Secret'}
            </button>
          </form>
        )}

        {secrets.length === 0 ? (
          <EmptyState
            icon="🔐"
            title="No secrets stored"
            description="Store API keys and credentials securely in encrypted workspace secrets"
          />
        ) : (
          <div className="space-y-2">
            {secrets.map((s) => (
              <div key={s.key || s.id} className="flex items-center justify-between p-3 bg-gray-800/40 rounded-lg">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-mono text-indigo-400">{s.key}</span>
                    {s.description && <span className="text-xs text-gray-500">· {s.description}</span>}
                  </div>
                  <div className="text-xs text-gray-600 mt-0.5">
                    {s.created_at ? `Added ${new Date(s.created_at).toLocaleDateString()}` : '—'}
                  </div>
                </div>
                <div className="flex items-center gap-3 ml-3">
                  <span className="text-xs text-gray-600 font-mono">••••••••</span>
                  <button onClick={() => handleDeleteSecret(s.key)} className="text-xs text-red-600 hover:text-red-400 transition-colors">
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Retention policy */}
      <div className="card">
        <h2 className="text-sm font-semibold text-white mb-4">Data Retention Policy</h2>
        {retention ? (
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-xs text-gray-500 mb-0.5">Policy Name</div>
              <div className="text-gray-200">{retention.name || 'Default'}</div>
            </div>
            <div>
              <div className="text-xs text-gray-500 mb-0.5">Retention Days</div>
              <div className="text-gray-200">{retention.retention_days || 90} days</div>
            </div>
            <div>
              <div className="text-xs text-gray-500 mb-0.5">Policy Type</div>
              <div className="text-gray-400 capitalize">{retention.policy_type || 'time_based'}</div>
            </div>
            <div>
              <div className="text-xs text-gray-500 mb-0.5">Action on Expiry</div>
              <div className="text-gray-400 capitalize">{retention.retention_action || 'delete'}</div>
            </div>
          </div>
        ) : (
          <div className="text-xs text-gray-500">
            No retention policy configured. Default: 90-day retention, delete on expiry.
          </div>
        )}
      </div>
    </div>
  );
}
