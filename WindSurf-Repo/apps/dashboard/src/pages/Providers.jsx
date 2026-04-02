import React, { useState, useEffect, useCallback } from 'react';
import { pluginsApi, appsApi } from '../utils/api';
import PageHeader from '../components/PageHeader';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';
import StatusBadge from '../components/StatusBadge';

export default function Providers() {
  const [plugins, setPlugins] = useState([]);
  const [apps, setApps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState({});
  const [msg, setMsg] = useState({ id: null, text: '', ok: true });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [pluginsRes, appsRes] = await Promise.all([
        pluginsApi.list().catch(() => ({ data: { available_plugins: [] } })),
        appsApi.list().catch(() => ({ data: [] })),
      ]);
      setPlugins(pluginsRes.data.available_plugins || []);
      setApps(Array.isArray(appsRes.data) ? appsRes.data : []);
    } catch { /* silent */ } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const toast = (id, text, ok = true) => {
    setMsg({ id, text, ok });
    setTimeout(() => setMsg({ id: null, text: '', ok: true }), 3000);
  };

  const togglePlugin = async (name, enabled) => {
    setToggling((t) => ({ ...t, [name]: true }));
    try {
      if (enabled) {
        await pluginsApi.disable(name);
        toast(name, `${name} disabled`, true);
      } else {
        await pluginsApi.enable(name);
        toast(name, `${name} enabled`, true);
      }
      await load();
    } catch (err) {
      toast(name, err.response?.data?.detail || 'Toggle failed', false);
    } finally {
      setToggling((t) => ({ ...t, [name]: false }));
    }
  };

  const toggleApp = async (app) => {
    setToggling((t) => ({ ...t, [app.id]: true }));
    try {
      if (app.workspace_has_access && app.workspace_is_active) {
        await appsApi.disable(app.id);
        toast(app.id, `${app.name} disabled`, true);
      } else {
        await appsApi.enable(app.id);
        toast(app.id, `${app.name} enabled`, true);
      }
      await load();
    } catch (err) {
      toast(app.id, err.response?.data?.detail || 'Toggle failed', false);
    } finally {
      setToggling((t) => ({ ...t, [app.id]: false }));
    }
  };

  if (loading) return <LoadingSpinner centered />;

  const PROVIDER_CARDS = [
    { name: 'Hugging Face', desc: 'Free-tier open-source models. Mistral, Whisper, embeddings.', icon: '🤗', status: 'healthy', key: 'huggingface' },
    { name: 'OpenAI', desc: 'GPT-4o-mini, Whisper-1. Only used when explicitly configured.', icon: '⚪', status: 'info', key: 'openai' },
    { name: 'Local LLM', desc: 'Self-hosted LLM via API. Zero cloud cost when running locally.', icon: '💻', status: 'info', key: 'local_llm' },
    { name: 'Local Whisper', desc: 'Self-hosted Whisper transcription. Zero per-call cost.', icon: '🎤', status: 'info', key: 'local_whisper' },
    { name: 'Anthropic Claude', desc: 'claude-3-haiku, claude-sonnet. Premium reasoning tasks.', icon: '🤖', status: 'info', key: 'anthropic' },
    { name: 'SERP API', desc: 'Web search results via SerpApi. Used for search operations.', icon: '🔍', status: 'info', key: 'serp' },
  ];

  return (
    <div className="space-y-6 max-w-5xl">
      <PageHeader
        title="Providers & Plugins"
        description="Manage AI providers and BYOS plugin extensions"
      />

      {/* AI Providers (static config info) */}
      <div>
        <h2 className="text-sm font-semibold text-white mb-3">AI Providers</h2>
        <p className="text-xs text-gray-500 mb-4">Providers are configured via environment variables. Set API keys in your .env to enable each provider.</p>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
          {PROVIDER_CARDS.map((p) => (
            <div key={p.key} className="card-sm flex items-start gap-3">
              <span className="text-2xl flex-shrink-0">{p.icon}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-white">{p.name}</span>
                </div>
                <p className="text-xs text-gray-500">{p.desc}</p>
                <div className="mt-2 text-xs text-gray-600 font-mono">
                  {p.key.toUpperCase()}_API_KEY
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Plugins */}
      <div>
        <h2 className="text-sm font-semibold text-white mb-3">Plugins</h2>
        {plugins.length === 0 ? (
          <EmptyState
            icon="🔌"
            title="No plugins available"
            description="Add plugin directories to apps/plugins/ to load extensions"
          />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {plugins.map((p) => (
              <div key={p.name} className="card flex items-start gap-3">
                <span className="text-xl flex-shrink-0">🔌</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium text-white">{p.name}</span>
                    <span className="text-xs text-gray-500">v{p.version || '1.0.0'}</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">{p.description || 'No description'}</p>
                  {msg.id === p.name && (
                    <div className={`text-xs mt-1 ${msg.ok ? 'text-emerald-400' : 'text-red-400'}`}>{msg.text}</div>
                  )}
                </div>
                <button
                  onClick={() => togglePlugin(p.name, p.enabled)}
                  disabled={toggling[p.name]}
                  className={`flex-shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${p.enabled ? 'bg-emerald-900/40 text-emerald-400 border border-emerald-800 hover:bg-red-900/40 hover:text-red-400 hover:border-red-800' : 'bg-gray-800 text-gray-400 border border-gray-700 hover:bg-indigo-900/40 hover:text-indigo-400 hover:border-indigo-800'}`}
                >
                  {toggling[p.name] ? '…' : p.enabled ? 'Enabled' : 'Disabled'}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Apps */}
      <div>
        <h2 className="text-sm font-semibold text-white mb-3">Built-in Apps</h2>
        {apps.length === 0 ? (
          <EmptyState icon="🚀" title="No apps found" description="Apps are seeded during initial setup" />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {apps.map((app) => {
              const active = app.workspace_has_access && app.workspace_is_active;
              return (
                <div key={app.id} className="card flex items-start gap-3">
                  {app.icon_url
                    ? <img src={app.icon_url} alt={app.name} className="w-8 h-8 rounded flex-shrink-0" />
                    : <span className="text-xl flex-shrink-0">🚀</span>
                  }
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-sm font-medium text-white">{app.name}</span>
                      <StatusBadge status={active ? 'healthy' : 'unhealthy'} label={active ? 'Active' : 'Inactive'} />
                    </div>
                    <p className="text-xs text-gray-500">{app.description || 'BYOS application'}</p>
                    {msg.id === app.id && (
                      <div className={`text-xs mt-1 ${msg.ok ? 'text-emerald-400' : 'text-red-400'}`}>{msg.text}</div>
                    )}
                  </div>
                  <button
                    onClick={() => toggleApp(app)}
                    disabled={toggling[app.id]}
                    className={`flex-shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border ${active ? 'bg-red-900/40 text-red-400 border-red-800 hover:bg-red-900/60' : 'bg-gray-800 text-gray-400 border-gray-700 hover:bg-indigo-900/40 hover:text-indigo-400 hover:border-indigo-800'}`}
                  >
                    {toggling[app.id] ? '…' : active ? 'Disable' : 'Enable'}
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
