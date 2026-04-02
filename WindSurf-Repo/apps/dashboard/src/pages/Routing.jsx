import React, { useState, useEffect, useCallback } from 'react';
import { routingApi } from '../utils/api';
import PageHeader from '../components/PageHeader';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import LoadingSpinner from '../components/LoadingSpinner';

const STRATEGIES = ['cost_optimized', 'quality_optimized', 'speed_optimized', 'hybrid'];
const PROVIDERS_LIST = ['huggingface', 'openai', 'anthropic', 'local'];

export default function Routing() {
  const [policy, setPolicy] = useState(null);
  const [history, setHistory] = useState([]);
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [saveMsg, setSaveMsg] = useState('');
  const [form, setForm] = useState({
    strategy: 'cost_optimized',
    max_cost: '',
    min_quality: '',
    max_latency_ms: '',
    allowed_providers: [],
    enforcement_mode: 'strict',
  });
  const [testForm, setTestForm] = useState({ operation_type: 'transcribe', input_text: '' });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [policyRes, histRes, provRes] = await Promise.all([
        routingApi.getPolicy().catch(() => ({ data: null })),
        routingApi.getHistory(50).catch(() => ({ data: { decisions: [] } })),
        routingApi.getProviders().catch(() => ({ data: { providers: [] } })),
      ]);
      if (policyRes.data) {
        const p = policyRes.data;
        setPolicy(p);
        const c = typeof p.constraints_json === 'string' ? JSON.parse(p.constraints_json) : (p.constraints || {});
        setForm({
          strategy: p.strategy || 'cost_optimized',
          max_cost: c.max_cost || '',
          min_quality: c.min_quality || '',
          max_latency_ms: c.max_latency_ms || '',
          allowed_providers: c.allowed_providers || [],
          enforcement_mode: c.enforcement_mode || 'strict',
        });
      }
      setHistory(histRes.data.decisions || histRes.data || []);
      setProviders(provRes.data.providers || []);
    } catch { /* silent */ } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setSaveMsg('');
    try {
      await routingApi.setPolicy({
        strategy: form.strategy,
        max_cost: form.max_cost ? parseFloat(form.max_cost) : null,
        min_quality: form.min_quality ? parseFloat(form.min_quality) : null,
        max_latency_ms: form.max_latency_ms ? parseInt(form.max_latency_ms, 10) : null,
        allowed_providers: form.allowed_providers.length > 0 ? form.allowed_providers : null,
        enforcement_mode: form.enforcement_mode,
      });
      setSaveMsg('Policy saved successfully');
      await load();
    } catch (err) {
      setSaveMsg(err.response?.data?.detail || 'Failed to save policy');
    } finally {
      setSaving(false);
      setTimeout(() => setSaveMsg(''), 3000);
    }
  };

  const handleTest = async (e) => {
    e.preventDefault();
    setTesting(true);
    setTestResult(null);
    try {
      const res = await routingApi.test({
        operation_type: testForm.operation_type,
        input_text: testForm.input_text,
        constraints: form,
      });
      setTestResult(res.data);
    } catch (err) {
      setTestResult({ error: err.response?.data?.detail || 'Test failed' });
    } finally {
      setTesting(false);
    }
  };

  const toggleProvider = (p) => {
    setForm((f) => ({
      ...f,
      allowed_providers: f.allowed_providers.includes(p)
        ? f.allowed_providers.filter((x) => x !== p)
        : [...f.allowed_providers, p],
    }));
  };

  const historyCols = [
    { key: 'created_at', label: 'Time', render: (v) => v ? <span className="text-xs text-gray-400">{new Date(v).toLocaleString()}</span> : '—' },
    { key: 'operation_type', label: 'Operation', render: (v) => <span className="capitalize text-gray-300">{v}</span> },
    { key: 'selected_provider', label: 'Selected Provider', render: (v) => <span className="capitalize text-indigo-400">{v}</span> },
    { key: 'routing_strategy', label: 'Strategy', render: (v) => <span className="capitalize text-gray-400">{v?.replace(/_/g, ' ')}</span> },
    { key: 'predicted_cost', label: 'Pred. Cost', render: (v) => v != null ? <span className="font-mono text-xs text-emerald-400">${Number(v).toFixed(6)}</span> : '—' },
    { key: 'actual_cost', label: 'Actual Cost', render: (v) => v != null ? <span className="font-mono text-xs">${Number(v).toFixed(6)}</span> : '—' },
  ];

  if (loading) return <LoadingSpinner centered />;

  return (
    <div className="space-y-6 max-w-5xl">
      <PageHeader
        title="Intelligent Routing"
        description="Route AI requests to the cheapest or best provider automatically"
      />

      {/* Routing policy config */}
      <div className="card">
        <h2 className="text-sm font-semibold text-white mb-4">Routing Policy</h2>
        <form onSubmit={handleSave} className="space-y-4">
          {/* Strategy selection */}
          <div>
            <label className="label">Strategy</label>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
              {STRATEGIES.map((s) => (
                <button key={s} type="button"
                  onClick={() => setForm((f) => ({ ...f, strategy: s }))}
                  className={`px-3 py-2 rounded-lg text-xs font-medium text-center transition-colors border ${form.strategy === s ? 'bg-indigo-600 border-indigo-500 text-white' : 'bg-gray-800 border-gray-700 text-gray-400 hover:bg-gray-700'}`}>
                  {s.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                </button>
              ))}
            </div>
          </div>

          {/* Constraints */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
            <div>
              <label className="label">Max Cost per Request ($)</label>
              <input type="number" step="0.0001" min="0" className="input" placeholder="No limit"
                value={form.max_cost} onChange={(e) => setForm((f) => ({ ...f, max_cost: e.target.value }))} />
            </div>
            <div>
              <label className="label">Min Quality Score (0–1)</label>
              <input type="number" step="0.01" min="0" max="1" className="input" placeholder="No minimum"
                value={form.min_quality} onChange={(e) => setForm((f) => ({ ...f, min_quality: e.target.value }))} />
            </div>
            <div>
              <label className="label">Max Latency (ms)</label>
              <input type="number" min="0" className="input" placeholder="No limit"
                value={form.max_latency_ms} onChange={(e) => setForm((f) => ({ ...f, max_latency_ms: e.target.value }))} />
            </div>
          </div>

          {/* Allowed providers */}
          <div>
            <label className="label">Allowed Providers (empty = all)</label>
            <div className="flex gap-2 flex-wrap">
              {PROVIDERS_LIST.map((p) => (
                <button key={p} type="button"
                  onClick={() => toggleProvider(p)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border capitalize ${form.allowed_providers.includes(p) ? 'bg-indigo-600 border-indigo-500 text-white' : 'bg-gray-800 border-gray-700 text-gray-400 hover:bg-gray-700'}`}>
                  {p}
                </button>
              ))}
            </div>
          </div>

          {/* Enforcement mode */}
          <div>
            <label className="label">Enforcement Mode</label>
            <div className="flex gap-2">
              {['strict', 'fallback'].map((m) => (
                <button key={m} type="button"
                  onClick={() => setForm((f) => ({ ...f, enforcement_mode: m }))}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-colors border ${form.enforcement_mode === m ? 'bg-indigo-600 border-indigo-500 text-white' : 'bg-gray-800 border-gray-700 text-gray-400'}`}>
                  {m}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button type="submit" className="btn-primary text-xs" disabled={saving}>
              {saving ? 'Saving…' : 'Save Policy'}
            </button>
            {saveMsg && (
              <span className={`text-xs ${saveMsg.includes('success') ? 'text-emerald-400' : 'text-red-400'}`}>
                {saveMsg}
              </span>
            )}
          </div>
        </form>
      </div>

      {/* Test routing */}
      <div className="card">
        <h2 className="text-sm font-semibold text-white mb-4">Test Routing Decision</h2>
        <form onSubmit={handleTest} className="flex gap-3 items-end">
          <div className="flex-1">
            <label className="label">Operation Type</label>
            <input type="text" className="input" placeholder="transcribe"
              value={testForm.operation_type}
              onChange={(e) => setTestForm((f) => ({ ...f, operation_type: e.target.value }))} />
          </div>
          <div className="flex-1">
            <label className="label">Sample Input</label>
            <input type="text" className="input" placeholder="Test input text"
              value={testForm.input_text}
              onChange={(e) => setTestForm((f) => ({ ...f, input_text: e.target.value }))} />
          </div>
          <button type="submit" className="btn-secondary text-xs flex-shrink-0" disabled={testing}>
            {testing ? 'Testing…' : '▶ Test'}
          </button>
        </form>

        {testResult && (
          <div className="mt-4 p-4 bg-gray-800/60 rounded-lg">
            {testResult.error ? (
              <div className="text-sm text-red-400">{testResult.error}</div>
            ) : (
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
                <div>
                  <div className="text-xs text-gray-500">Selected Provider</div>
                  <div className="font-semibold text-indigo-400 capitalize">{testResult.selected_provider || testResult.provider || '—'}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">Strategy Applied</div>
                  <div className="text-gray-300 capitalize">{(testResult.strategy || '—').replace(/_/g, ' ')}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">Predicted Cost</div>
                  <div className="text-emerald-400 font-mono">${Number(testResult.predicted_cost || 0).toFixed(6)}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">Confidence</div>
                  <div className="text-gray-300">{testResult.confidence ? `${(testResult.confidence * 100).toFixed(0)}%` : '—'}</div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Routing history */}
      <div className="card p-0">
        <div className="px-5 py-4 border-b border-gray-800">
          <h2 className="text-sm font-semibold text-white">Routing Decision History</h2>
        </div>
        <DataTable
          columns={historyCols}
          rows={history}
          loading={false}
          emptyIcon="🔀"
          emptyTitle="No routing decisions yet"
          emptyDesc="Decisions will appear as AI requests are routed through BYOS"
          keyField="id"
        />
      </div>
    </div>
  );
}
