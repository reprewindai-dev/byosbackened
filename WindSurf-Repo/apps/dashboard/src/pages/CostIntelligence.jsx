import React, { useState, useEffect, useCallback } from 'react';
import { costApi } from '../utils/api';
import PageHeader from '../components/PageHeader';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import LoadingSpinner from '../components/LoadingSpinner';
import MetricCard from '../components/MetricCard';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

const OPERATION_TYPES = ['transcribe', 'chat', 'embed', 'search', 'summarize', 'extract', 'other'];
const PROVIDERS = ['huggingface', 'openai', 'local', 'anthropic'];

export default function CostIntelligence() {
  const [summary, setSummary] = useState(null);
  const [history, setHistory] = useState([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [predicting, setPredicting] = useState(false);
  const [prediction, setPrediction] = useState(null);
  const [predError, setPredError] = useState('');
  const [summaryDays, setSummaryDays] = useState(30);

  const [predForm, setPredForm] = useState({
    operation_type: 'transcribe',
    provider: 'huggingface',
    input_tokens: 500,
    estimated_output_tokens: 200,
    model: '',
  });

  const limit = 50;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [sumRes, histRes] = await Promise.all([
        costApi.getSummary(summaryDays),
        costApi.getHistory(limit, offset),
      ]);
      setSummary(sumRes.data);
      setHistory(histRes.data.predictions || histRes.data.history || []);
      setTotal(histRes.data.total || 0);
    } catch (err) {
      // silence - show empty state
    } finally {
      setLoading(false);
    }
  }, [summaryDays, offset]);

  useEffect(() => { load(); }, [load]);

  const handlePredict = async (e) => {
    e.preventDefault();
    setPredicting(true);
    setPredError('');
    setPrediction(null);
    try {
      const res = await costApi.predict({
        ...predForm,
        input_tokens: parseInt(predForm.input_tokens, 10),
        estimated_output_tokens: parseInt(predForm.estimated_output_tokens, 10),
      });
      setPrediction(res.data);
    } catch (err) {
      setPredError(err.response?.data?.detail || 'Prediction failed');
    } finally {
      setPredicting(false);
    }
  };

  const cols = [
    { key: 'created_at', label: 'Time', render: (v) => v ? new Date(v).toLocaleString() : '—' },
    { key: 'operation_type', label: 'Operation' },
    { key: 'provider', label: 'Provider', render: (v) => <span className="capitalize">{v}</span> },
    { key: 'model', label: 'Model', render: (v) => <span className="text-gray-500">{v || '—'}</span> },
    { key: 'input_tokens', label: 'Input Tokens', render: (v) => Number(v || 0).toLocaleString() },
    { key: 'estimated_output_tokens', label: 'Est. Output', render: (v) => Number(v || 0).toLocaleString() },
    {
      key: 'predicted_cost', label: 'Predicted Cost',
      render: (v) => <span className="text-emerald-400 font-mono">${Number(v || 0).toFixed(6)}</span>
    },
    {
      key: 'accuracy_score', label: 'Confidence',
      render: (v) => v != null ? `${(Number(v) * 100).toFixed(0)}%` : '—'
    },
  ];

  return (
    <div className="space-y-6 max-w-7xl">
      <PageHeader
        title="Cost Intelligence"
        description="Predict, track and optimize your AI spending"
        actions={
          <div className="flex gap-1">
            {[7, 30, 90].map((d) => (
              <button key={d}
                onClick={() => setSummaryDays(d)}
                className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${summaryDays === d ? 'bg-indigo-600 text-white' : 'btn-secondary'}`}
              >{d}d</button>
            ))}
          </div>
        }
      />

      {/* Summary KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard title="Total Cost" value={`$${Number(summary?.total_cost || 0).toFixed(4)}`} icon="💰" color="amber" loading={loading} />
        <MetricCard title="Avg Cost/Op" value={`$${Number(summary?.avg_cost || 0).toFixed(6)}`} icon="📊" color="indigo" loading={loading} />
        <MetricCard title="Total Operations" value={Number(summary?.total_operations || 0).toLocaleString()} icon="⚡" color="blue" loading={loading} />
        <MetricCard title="Top Provider" value={summary?.top_provider || '—'} icon="🏆" color="emerald" loading={loading} />
      </div>

      {/* Provider cost bar chart */}
      {summary?.by_provider?.length > 0 && (
        <div className="card">
          <h2 className="text-sm font-semibold text-white mb-4">Cost by Provider</h2>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={summary.by_provider}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="provider" tick={{ fontSize: 11, fill: '#6b7280' }} />
              <YAxis tick={{ fontSize: 11, fill: '#6b7280' }} tickFormatter={(v) => `$${v}`} />
              <Tooltip
                contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: 8 }}
                formatter={(v) => [`$${Number(v).toFixed(6)}`, 'Cost']}
              />
              <Bar dataKey="total_cost" fill="#6366f1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Cost Prediction */}
      <div className="card">
        <h2 className="text-sm font-semibold text-white mb-4">Predict Operation Cost</h2>
        <form onSubmit={handlePredict}>
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-4">
            <div>
              <label className="label">Operation Type</label>
              <select className="input" value={predForm.operation_type}
                onChange={(e) => setPredForm((f) => ({ ...f, operation_type: e.target.value }))}>
                {OPERATION_TYPES.map((o) => <option key={o}>{o}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Provider</label>
              <select className="input" value={predForm.provider}
                onChange={(e) => setPredForm((f) => ({ ...f, provider: e.target.value }))}>
                {PROVIDERS.map((p) => <option key={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Input Tokens</label>
              <input type="number" className="input" value={predForm.input_tokens}
                onChange={(e) => setPredForm((f) => ({ ...f, input_tokens: e.target.value }))} min={1} />
            </div>
            <div>
              <label className="label">Est. Output Tokens</label>
              <input type="number" className="input" value={predForm.estimated_output_tokens}
                onChange={(e) => setPredForm((f) => ({ ...f, estimated_output_tokens: e.target.value }))} min={0} />
            </div>
            <div>
              <label className="label">Model (optional)</label>
              <input type="text" className="input" value={predForm.model} placeholder="e.g. gpt-4o-mini"
                onChange={(e) => setPredForm((f) => ({ ...f, model: e.target.value }))} />
            </div>
          </div>
          <button type="submit" className="btn-primary" disabled={predicting}>
            {predicting ? 'Predicting…' : 'Predict Cost'}
          </button>
        </form>

        {predError && (
          <div className="mt-3 p-3 bg-red-900/30 border border-red-800 rounded-lg text-sm text-red-400">{predError}</div>
        )}

        {prediction && (
          <div className="mt-4 p-4 bg-gray-800/60 rounded-lg">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <div className="text-xs text-gray-500">Predicted Cost</div>
                <div className="text-xl font-bold text-emerald-400 font-mono">${Number(prediction.predicted_cost).toFixed(6)}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Confidence Range</div>
                <div className="text-sm text-gray-300 font-mono">
                  ${Number(prediction.confidence_lower).toFixed(6)} – ${Number(prediction.confidence_upper).toFixed(6)}
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Accuracy Score</div>
                <div className="text-sm text-gray-300">{(Number(prediction.accuracy_score) * 100).toFixed(0)}%</div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Prediction ID</div>
                <div className="text-xs text-gray-500 font-mono truncate">{prediction.prediction_id}</div>
              </div>
            </div>
            {prediction.alternative_providers?.length > 0 && (
              <div className="mt-3">
                <div className="text-xs text-gray-500 mb-2">Alternative Providers</div>
                <div className="flex flex-wrap gap-2">
                  {prediction.alternative_providers.map((alt) => (
                    <div key={alt.provider} className="px-2 py-1 bg-gray-700 rounded text-xs">
                      <span className="capitalize text-gray-300">{alt.provider}</span>
                      <span className="text-emerald-400 ml-1.5">${Number(alt.cost || 0).toFixed(6)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Prediction history */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-white">Prediction History</h2>
          <span className="text-xs text-gray-500">{total} total</span>
        </div>
        <DataTable
          columns={cols}
          rows={history}
          loading={loading}
          emptyIcon="💰"
          emptyTitle="No predictions yet"
          emptyDesc="Use the form above to predict operation costs"
          keyField="id"
        />
        {total > limit && (
          <div className="flex justify-between items-center mt-4 pt-4 border-t border-gray-800">
            <button className="btn-secondary text-xs" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>← Prev</button>
            <span className="text-xs text-gray-500">{offset + 1}–{Math.min(offset + limit, total)} of {total}</span>
            <button className="btn-secondary text-xs" disabled={offset + limit >= total} onClick={() => setOffset(offset + limit)}>Next →</button>
          </div>
        )}
      </div>
    </div>
  );
}
