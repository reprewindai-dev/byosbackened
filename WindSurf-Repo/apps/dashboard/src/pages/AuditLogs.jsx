import React, { useState, useEffect, useCallback } from 'react';
import { auditApi } from '../utils/api';
import PageHeader from '../components/PageHeader';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import LoadingSpinner from '../components/LoadingSpinner';

const LIMIT = 50;

export default function AuditLogs() {
  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    operationType: '', provider: '', startDate: '', endDate: '',
  });
  const [appliedFilters, setAppliedFilters] = useState({});
  const [exportLoading, setExportLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await auditApi.getLogs({ ...appliedFilters, limit: LIMIT, offset });
      setLogs(res.data.logs || []);
      setTotal(res.data.total || 0);
    } catch {
      setLogs([]);
    } finally {
      setLoading(false);
    }
  }, [appliedFilters, offset]);

  useEffect(() => { load(); }, [load]);

  const applyFilters = (e) => {
    e.preventDefault();
    setOffset(0);
    setAppliedFilters({ ...filters });
  };

  const clearFilters = () => {
    setFilters({ operationType: '', provider: '', startDate: '', endDate: '' });
    setAppliedFilters({});
    setOffset(0);
  };

  const cols = [
    {
      key: 'created_at', label: 'Time',
      render: (v) => v ? <span className="text-xs text-gray-400">{new Date(v).toLocaleString()}</span> : '—'
    },
    { key: 'operation_type', label: 'Operation', render: (v) => <span className="capitalize text-gray-300">{v}</span> },
    { key: 'provider', label: 'Provider', render: (v) => <span className="capitalize text-gray-400">{v || '—'}</span> },
    { key: 'model', label: 'Model', render: (v) => <span className="text-gray-600 font-mono text-xs">{v || '—'}</span> },
    {
      key: 'cost', label: 'Cost',
      render: (v) => <span className="text-emerald-400 font-mono text-xs">${Number(v || 0).toFixed(6)}</span>
    },
    {
      key: 'pii_detected', label: 'PII',
      render: (v) => v ? <StatusBadge status="warning" label="PII Detected" /> : <span className="text-gray-600 text-xs">Clean</span>
    },
    {
      key: 'input_preview', label: 'Input Preview',
      render: (v) => <span className="text-gray-500 text-xs truncate max-w-xs block">{v ? v.slice(0, 60) + (v.length > 60 ? '…' : '') : '—'}</span>
    },
  ];

  const hasActiveFilters = Object.values(appliedFilters).some(Boolean);

  return (
    <div className="space-y-6 max-w-7xl">
      <PageHeader
        title="Audit Logs"
        description="Tamper-proof AI operation history with full traceability"
        actions={
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">{total.toLocaleString()} records</span>
            <button onClick={load} className="btn-secondary text-xs">↻ Refresh</button>
          </div>
        }
      />

      {/* Filters */}
      <div className="card">
        <form onSubmit={applyFilters}>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-3">
            <div>
              <label className="label">Operation Type</label>
              <input type="text" className="input" placeholder="e.g. transcribe"
                value={filters.operationType}
                onChange={(e) => setFilters((f) => ({ ...f, operationType: e.target.value }))} />
            </div>
            <div>
              <label className="label">Provider</label>
              <input type="text" className="input" placeholder="e.g. openai"
                value={filters.provider}
                onChange={(e) => setFilters((f) => ({ ...f, provider: e.target.value }))} />
            </div>
            <div>
              <label className="label">Start Date</label>
              <input type="datetime-local" className="input"
                value={filters.startDate}
                onChange={(e) => setFilters((f) => ({ ...f, startDate: e.target.value }))} />
            </div>
            <div>
              <label className="label">End Date</label>
              <input type="datetime-local" className="input"
                value={filters.endDate}
                onChange={(e) => setFilters((f) => ({ ...f, endDate: e.target.value }))} />
            </div>
          </div>
          <div className="flex gap-2">
            <button type="submit" className="btn-primary text-xs">Apply Filters</button>
            {hasActiveFilters && (
              <button type="button" onClick={clearFilters} className="btn-secondary text-xs">Clear</button>
            )}
          </div>
        </form>
      </div>

      {/* Table */}
      <div className="card p-0">
        <div className="px-5 py-4 border-b border-gray-800 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">Log Entries</h2>
          {hasActiveFilters && (
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
              <span className="text-xs text-gray-400">Filters active</span>
            </div>
          )}
        </div>
        <DataTable
          columns={cols}
          rows={logs}
          loading={loading}
          emptyIcon="🔍"
          emptyTitle="No audit logs found"
          emptyDesc="AI operations will appear here once they're executed through BYOS"
          keyField="id"
        />
        {total > LIMIT && (
          <div className="flex justify-between items-center px-5 py-3 border-t border-gray-800">
            <button className="btn-secondary text-xs" disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - LIMIT))}>← Previous</button>
            <span className="text-xs text-gray-500">
              {offset + 1}–{Math.min(offset + LIMIT, total)} of {total.toLocaleString()}
            </span>
            <button className="btn-secondary text-xs" disabled={offset + LIMIT >= total}
              onClick={() => setOffset(offset + LIMIT)}>Next →</button>
          </div>
        )}
      </div>
    </div>
  );
}
