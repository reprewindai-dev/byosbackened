import React, { useState, useEffect, useCallback } from 'react';
import { anomaliesApi } from '../utils/api';
import PageHeader from '../components/PageHeader';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';

export default function Anomalies() {
  const [anomalies, setAnomalies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [detecting, setDetecting] = useState(false);
  const [statusFilter, setStatusFilter] = useState('');
  const [detectMsg, setDetectMsg] = useState('');
  const [detectForm, setDetectForm] = useState({ lookback_minutes: 60, spike_multiplier: 3.0, min_events: 5 });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await anomaliesApi.list(statusFilter);
      setAnomalies(res.data.anomalies || res.data || []);
    } catch { setAnomalies([]); } finally { setLoading(false); }
  }, [statusFilter]);

  useEffect(() => { load(); }, [load]);

  const handleDetect = async (e) => {
    e.preventDefault();
    setDetecting(true);
    setDetectMsg('');
    try {
      await anomaliesApi.detect({
        lookback_minutes: parseInt(detectForm.lookback_minutes, 10),
        spike_multiplier: parseFloat(detectForm.spike_multiplier),
        min_events: parseInt(detectForm.min_events, 10),
      });
      setDetectMsg('Detection run complete');
      await load();
    } catch (err) {
      setDetectMsg(err.response?.data?.detail || 'Detection failed');
    } finally {
      setDetecting(false);
      setTimeout(() => setDetectMsg(''), 4000);
    }
  };

  const handleUpdateStatus = async (id, status) => {
    try {
      await anomaliesApi.updateStatus(id, { status, resolution_notes: '' });
      await load();
    } catch (err) { alert(err.response?.data?.detail || 'Failed to update'); }
  };

  const cols = [
    { key: 'created_at', label: 'Detected', render: (v) => v ? <span className="text-xs text-gray-400">{new Date(v).toLocaleString()}</span> : '—' },
    { key: 'severity', label: 'Severity', render: (v) => <StatusBadge status={v} label={v} /> },
    { key: 'status', label: 'Status', render: (v) => <StatusBadge status={v} label={v} /> },
    { key: 'description', label: 'Description', render: (v) => <span className="text-gray-300 text-xs">{v || '—'}</span> },
    { key: 'anomaly_type', label: 'Type', render: (v) => <span className="text-gray-500 text-xs capitalize">{(v || '').replace(/_/g, ' ')}</span> },
    {
      key: 'id', label: 'Actions',
      render: (id, row) => row.status !== 'RESOLVED' ? (
        <button onClick={() => handleUpdateStatus(id, 'RESOLVED')}
          className="text-xs text-emerald-400 hover:text-emerald-300 transition-colors">
          Resolve
        </button>
      ) : <span className="text-xs text-gray-600">—</span>
    },
  ];

  return (
    <div className="space-y-6 max-w-5xl">
      <PageHeader
        title="Anomaly Detection"
        description="Detect and resolve cost spikes and unusual activity"
        actions={
          <button onClick={load} className="btn-secondary text-xs">↻ Refresh</button>
        }
      />

      {/* Detection form */}
      <div className="card">
        <h2 className="text-sm font-semibold text-white mb-4">Run Detection</h2>
        <form onSubmit={handleDetect} className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="label">Lookback (min)</label>
            <input type="number" className="input w-28" value={detectForm.lookback_minutes}
              onChange={(e) => setDetectForm((f) => ({ ...f, lookback_minutes: e.target.value }))} />
          </div>
          <div>
            <label className="label">Spike Multiplier</label>
            <input type="number" step="0.1" className="input w-28" value={detectForm.spike_multiplier}
              onChange={(e) => setDetectForm((f) => ({ ...f, spike_multiplier: e.target.value }))} />
          </div>
          <div>
            <label className="label">Min Events</label>
            <input type="number" className="input w-24" value={detectForm.min_events}
              onChange={(e) => setDetectForm((f) => ({ ...f, min_events: e.target.value }))} />
          </div>
          <button type="submit" className="btn-primary text-xs" disabled={detecting}>
            {detecting ? '⏳ Running…' : '▶ Detect Anomalies'}
          </button>
          {detectMsg && (
            <span className={`text-xs self-center ${detectMsg.includes('complete') ? 'text-emerald-400' : 'text-red-400'}`}>
              {detectMsg}
            </span>
          )}
        </form>
      </div>

      {/* Filter */}
      <div className="flex gap-2">
        {['', 'OPEN', 'RESOLVED', 'IGNORED'].map((s) => (
          <button key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${statusFilter === s ? 'bg-indigo-600 text-white' : 'btn-secondary'}`}>
            {s || 'All'}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="card p-0">
        <div className="px-5 py-4 border-b border-gray-800">
          <h2 className="text-sm font-semibold text-white">Anomalies</h2>
        </div>
        <DataTable
          columns={cols}
          rows={anomalies}
          loading={loading}
          emptyIcon="✅"
          emptyTitle="No anomalies detected"
          emptyDesc="Run detection or wait for the system to detect cost spikes automatically"
          keyField="id"
        />
      </div>
    </div>
  );
}
