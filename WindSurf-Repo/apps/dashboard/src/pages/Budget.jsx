import React, { useState, useEffect, useCallback } from 'react';
import { budgetApi } from '../utils/api';
import PageHeader from '../components/PageHeader';
import StatusBadge from '../components/StatusBadge';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';

const BUDGET_TYPES = ['daily', 'monthly', 'project', 'client'];

const defaultForm = {
  budget_type: 'monthly',
  amount: '',
  period_start: '',
  period_end: '',
  alert_thresholds: [50, 80, 95],
};

export default function Budget() {
  const [budgets, setBudgets] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(defaultForm);
  const [formError, setFormError] = useState('');
  const [editingId, setEditingId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [budgetsRes, alertsRes] = await Promise.all([
        budgetApi.list(),
        budgetApi.getAlerts().catch(() => ({ data: { alerts: [] } })),
      ]);
      setBudgets(budgetsRes.data.budgets || budgetsRes.data || []);
      setAlerts(alertsRes.data.alerts || []);
    } catch {
      setBudgets([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.amount || isNaN(parseFloat(form.amount))) {
      setFormError('Amount is required');
      return;
    }
    setSaving(true);
    setFormError('');
    try {
      const payload = {
        budget_type: form.budget_type,
        amount: parseFloat(form.amount),
        period_start: form.period_start || undefined,
        period_end: form.period_end || undefined,
        alert_thresholds: form.alert_thresholds,
      };
      if (editingId) {
        await budgetApi.update(editingId, payload);
      } else {
        await budgetApi.create(payload);
      }
      setShowForm(false);
      setForm(defaultForm);
      setEditingId(null);
      await load();
    } catch (err) {
      setFormError(err.response?.data?.detail || 'Failed to save budget');
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (b) => {
    setEditingId(b.id);
    setForm({
      budget_type: b.budget_type,
      amount: b.amount?.toString() || '',
      period_start: b.period_start ? b.period_start.slice(0, 16) : '',
      period_end: b.period_end ? b.period_end.slice(0, 16) : '',
      alert_thresholds: b.alert_thresholds || [50, 80, 95],
    });
    setShowForm(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this budget?')) return;
    try {
      await budgetApi.delete(id);
      await load();
    } catch (err) {
      alert(err.response?.data?.detail || 'Delete failed');
    }
  };

  const toggleForm = () => {
    setShowForm((p) => !p);
    if (showForm) { setForm(defaultForm); setEditingId(null); setFormError(''); }
  };

  if (loading) return <LoadingSpinner centered />;

  return (
    <div className="space-y-6 max-w-5xl">
      <PageHeader
        title="Budget Management"
        description="Set spend limits and alert thresholds for AI operations"
        actions={
          <button onClick={toggleForm} className="btn-primary text-xs">
            {showForm ? '✕ Cancel' : '+ New Budget'}
          </button>
        }
      />

      {/* Alert banners */}
      {alerts.length > 0 && (
        <div className="space-y-2">
          {alerts.map((alert, i) => (
            <div key={i} className="p-3 bg-amber-900/30 border border-amber-800 rounded-lg flex items-center gap-3">
              <span className="text-xl">⚠️</span>
              <div>
                <div className="text-sm font-medium text-amber-400">{alert.message || 'Budget alert'}</div>
                {alert.detail && <div className="text-xs text-amber-600 mt-0.5">{alert.detail}</div>}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create/Edit form */}
      {showForm && (
        <div className="card border-indigo-800/50">
          <h2 className="text-sm font-semibold text-white mb-4">
            {editingId ? 'Edit Budget' : 'Create Budget'}
          </h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            {formError && (
              <div className="p-3 bg-red-900/30 border border-red-800 rounded-lg text-sm text-red-400">{formError}</div>
            )}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <div>
                <label className="label">Budget Type</label>
                <select className="input" value={form.budget_type}
                  onChange={(e) => setForm((f) => ({ ...f, budget_type: e.target.value }))}>
                  {BUDGET_TYPES.map((t) => <option key={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label className="label">Amount (USD)</label>
                <input type="number" step="0.01" min="0.01" className="input" placeholder="e.g. 100.00"
                  value={form.amount} onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))} required />
              </div>
              <div>
                <label className="label">Period Start</label>
                <input type="datetime-local" className="input"
                  value={form.period_start} onChange={(e) => setForm((f) => ({ ...f, period_start: e.target.value }))} />
              </div>
              <div>
                <label className="label">Period End</label>
                <input type="datetime-local" className="input"
                  value={form.period_end} onChange={(e) => setForm((f) => ({ ...f, period_end: e.target.value }))} />
              </div>
            </div>
            <div>
              <label className="label">Alert Thresholds (%)</label>
              <div className="flex gap-2">
                {[25, 50, 75, 80, 90, 95, 100].map((pct) => (
                  <label key={pct} className="flex items-center gap-1 text-xs text-gray-400 cursor-pointer">
                    <input type="checkbox"
                      className="rounded border-gray-600 bg-gray-800"
                      checked={form.alert_thresholds.includes(pct)}
                      onChange={(e) => {
                        const current = form.alert_thresholds;
                        setForm((f) => ({
                          ...f,
                          alert_thresholds: e.target.checked
                            ? [...current, pct].sort((a, b) => a - b)
                            : current.filter((t) => t !== pct),
                        }));
                      }}
                    />
                    {pct}%
                  </label>
                ))}
              </div>
            </div>
            <div className="flex gap-2">
              <button type="submit" className="btn-primary text-xs" disabled={saving}>
                {saving ? 'Saving…' : editingId ? 'Update Budget' : 'Create Budget'}
              </button>
              <button type="button" className="btn-secondary text-xs" onClick={toggleForm}>Cancel</button>
            </div>
          </form>
        </div>
      )}

      {/* Budget list */}
      {budgets.length === 0 ? (
        <EmptyState
          icon="📊"
          title="No budgets configured"
          description="Create a budget to track and limit your AI spending"
          action={<button onClick={toggleForm} className="btn-primary text-xs">Create First Budget</button>}
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {budgets.map((b) => {
            const pct = b.utilization_pct ?? (b.amount > 0 ? (b.spent / b.amount) * 100 : 0);
            const status = pct >= 95 ? 'critical' : pct >= 80 ? 'warning' : 'healthy';
            const spent = b.spent ?? 0;
            const amount = b.amount ?? 0;
            return (
              <div key={b.id} className="card">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-white capitalize">{b.budget_type} Budget</span>
                      <StatusBadge status={status} />
                    </div>
                    {b.period_start && b.period_end && (
                      <div className="text-xs text-gray-500 mt-0.5">
                        {new Date(b.period_start).toLocaleDateString()} – {new Date(b.period_end).toLocaleDateString()}
                      </div>
                    )}
                  </div>
                  <div className="flex gap-1.5">
                    <button onClick={() => handleEdit(b)} className="text-xs text-gray-500 hover:text-gray-300 transition-colors">Edit</button>
                    <button onClick={() => handleDelete(b.id)} className="text-xs text-red-600 hover:text-red-400 transition-colors">Delete</button>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="mb-3">
                  <div className="flex justify-between text-xs text-gray-400 mb-1">
                    <span>${spent.toFixed(2)} spent</span>
                    <span>${amount.toFixed(2)} limit</span>
                  </div>
                  <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${status === 'critical' ? 'bg-red-500' : status === 'warning' ? 'bg-amber-500' : 'bg-emerald-500'}`}
                      style={{ width: `${Math.min(pct, 100)}%` }}
                    />
                  </div>
                  <div className="text-right text-xs text-gray-500 mt-1">{pct.toFixed(1)}% used · ${Math.max(0, amount - spent).toFixed(2)} remaining</div>
                </div>

                {/* Alert thresholds */}
                {b.alerts_sent?.length > 0 && (
                  <div className="flex items-center gap-1 flex-wrap">
                    <span className="text-xs text-gray-500">Alerts:</span>
                    {b.alerts_sent.map((t) => (
                      <span key={t} className={`px-1.5 py-0.5 rounded text-xs font-medium ${pct >= t ? 'bg-red-900/50 text-red-400' : 'bg-gray-800 text-gray-500'}`}>
                        {t}%
                      </span>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
