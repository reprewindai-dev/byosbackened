import React, { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts';
import { dashboardApi } from '../utils/api';
import MetricCard from '../components/MetricCard';
import StatusBadge from '../components/StatusBadge';
import PageHeader from '../components/PageHeader';
import LoadingSpinner from '../components/LoadingSpinner';

const PROVIDER_COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [status, setStatus] = useState(null);
  const [activity, setActivity] = useState([]);
  const [costTrend, setCostTrend] = useState([]);
  const [providerBreakdown, setProviderBreakdown] = useState([]);
  const [savings, setSavings] = useState(null);
  const [anomalies, setAnomalies] = useState(null);
  const [budgets, setBudgets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [trendDays, setTrendDays] = useState(7);

  const load = useCallback(async () => {
    try {
      const [
        statsRes, statusRes, activityRes, trendRes,
        providerRes, savingsRes, anomaliesRes, budgetsRes,
      ] = await Promise.all([
        dashboardApi.getStats(),
        dashboardApi.getSystemStatus(),
        dashboardApi.getRecentActivity(15),
        dashboardApi.getCostTrend(trendDays),
        dashboardApi.getProviderBreakdown(),
        dashboardApi.getSavingsSummary(),
        dashboardApi.getAnomaliesSummary(),
        dashboardApi.getBudgetStatus(),
      ]);
      setStats(statsRes.data);
      setStatus(statusRes.data);
      setActivity(activityRes.data.activities || []);
      setCostTrend(trendRes.data.trend || []);
      setProviderBreakdown(providerRes.data.breakdown || []);
      setSavings(savingsRes.data);
      setAnomalies(anomaliesRes.data);
      setBudgets(budgetsRes.data.budgets || []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  }, [trendDays]);

  useEffect(() => { load(); }, [load]);

  // Auto-refresh every 30s
  useEffect(() => {
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, [load]);

  if (loading) return <LoadingSpinner centered />;

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <div className="text-3xl">⚠️</div>
        <p className="text-sm text-red-400">{error}</p>
        <button onClick={load} className="btn-secondary text-xs">Retry</button>
      </div>
    );
  }

  const fmtCurrency = (v) => `$${Number(v || 0).toFixed(2)}`;
  const fmtNum = (v) => Number(v || 0).toLocaleString();

  return (
    <div className="space-y-6 max-w-7xl">
      <PageHeader
        title="Overview"
        description="Real-time system health and cost intelligence"
        actions={
          <button onClick={load} className="btn-secondary text-xs">
            ↻ Refresh
          </button>
        }
      />

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard title="Total Requests" value={fmtNum(stats?.totalRequests)} subtitle={`${fmtNum(stats?.requestsToday)} today`} icon="⚡" color="indigo" />
        <MetricCard title="Monthly Cost" value={fmtCurrency(stats?.monthlyCost)} subtitle="This month's spend" icon="💰" color="amber" />
        <MetricCard title="Total Savings" value={fmtCurrency(stats?.totalSavings)} subtitle={`${savings?.savingsPercent || 0}% vs baseline`} icon="📉" color="emerald" />
        <MetricCard title="System Health" value={`${stats?.systemHealth || 0}%`} subtitle={`${stats?.openAnomalies || 0} open anomalies`} icon="❤️" color={stats?.systemHealth >= 90 ? 'emerald' : 'amber'} />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard title="Active Users" value={fmtNum(stats?.totalUsers)} icon="👥" color="blue" />
        <MetricCard title="Running Apps" value={fmtNum(stats?.runningApps)} icon="🚀" color="purple" />
        <MetricCard title="Error Rate" value={`${((stats?.errorRate || 0) * 100).toFixed(2)}%`} icon="🔴" color={stats?.errorRate < 0.05 ? 'emerald' : 'red'} />
        <MetricCard title="Workspaces" value={fmtNum(stats?.activeWorkspaces)} icon="🏢" color="indigo" />
      </div>

      {/* Cost trend + provider breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="card lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-white">Cost Trend</h2>
            <div className="flex gap-1">
              {[7, 14, 30].map((d) => (
                <button
                  key={d}
                  onClick={() => setTrendDays(d)}
                  className={`px-2 py-1 rounded text-xs font-medium transition-colors ${trendDays === d ? 'bg-indigo-600 text-white' : 'text-gray-500 hover:text-gray-300'}`}
                >
                  {d}d
                </button>
              ))}
            </div>
          </div>
          {costTrend.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={costTrend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#6b7280' }} tickFormatter={(v) => v.slice(5)} />
                <YAxis tick={{ fontSize: 11, fill: '#6b7280' }} tickFormatter={(v) => `$${v.toFixed(2)}`} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: 8 }}
                  labelStyle={{ color: '#9ca3af', fontSize: 11 }}
                  formatter={(v) => [`$${Number(v).toFixed(4)}`, 'Cost']}
                />
                <Line type="monotone" dataKey="cost" stroke="#6366f1" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-48 text-gray-600 text-sm">No cost data yet</div>
          )}
        </div>

        <div className="card">
          <h2 className="text-sm font-semibold text-white mb-4">Provider Breakdown</h2>
          {providerBreakdown.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie data={providerBreakdown} dataKey="totalCost" nameKey="provider" cx="50%" cy="50%" outerRadius={65} innerRadius={40}>
                    {providerBreakdown.map((_, i) => (
                      <Cell key={i} fill={PROVIDER_COLORS[i % PROVIDER_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: 8 }}
                    formatter={(v) => [`$${Number(v).toFixed(4)}`, 'Cost']}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-1.5 mt-2">
                {providerBreakdown.map((p, i) => (
                  <div key={p.provider} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full" style={{ backgroundColor: PROVIDER_COLORS[i % PROVIDER_COLORS.length] }} />
                      <span className="text-gray-400 capitalize">{p.provider}</span>
                    </div>
                    <span className="text-gray-300">{p.requests} reqs · ${Number(p.totalCost).toFixed(4)}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="flex items-center justify-center h-48 text-gray-600 text-sm">No provider data yet</div>
          )}
        </div>
      </div>

      {/* System status + recent activity + budget */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* System status */}
        <div className="card">
          <h2 className="text-sm font-semibold text-white mb-4">System Status</h2>
          <div className="space-y-3">
            {(status?.services || []).map((svc) => (
              <div key={svc.name} className="flex items-center justify-between">
                <div className="min-w-0">
                  <div className="text-sm text-gray-300 font-medium">{svc.name}</div>
                  <div className="text-xs text-gray-600 truncate">{svc.description}</div>
                </div>
                <StatusBadge status={svc.status} />
              </div>
            ))}
          </div>
        </div>

        {/* Recent activity */}
        <div className="card lg:col-span-1">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-white">Recent Activity</h2>
            <Link to="/audit" className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors">View all →</Link>
          </div>
          {activity.length > 0 ? (
            <div className="space-y-2.5">
              {activity.slice(0, 8).map((a) => (
                <div key={a.id} className="flex items-start gap-2">
                  <span className={`w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0 ${a.severity === 'high' ? 'bg-red-400' : 'bg-gray-600'}`} />
                  <div className="min-w-0 flex-1">
                    <div className="text-xs text-gray-300 truncate">{a.action}</div>
                    <div className="text-xs text-gray-600">{new Date(a.timestamp).toLocaleTimeString()}</div>
                  </div>
                  {a.piiDetected && (
                    <span className="badge-warning text-xs flex-shrink-0">PII</span>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center text-gray-600 text-sm py-6">No activity yet</div>
          )}
        </div>

        {/* Budget status */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-white">Budget Status</h2>
            <Link to="/budget" className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors">Manage →</Link>
          </div>
          {budgets.length > 0 ? (
            <div className="space-y-3">
              {budgets.map((b) => (
                <div key={b.id}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-gray-400 capitalize">{b.budgetType}</span>
                    <span className="text-xs text-gray-400">{b.utilizationPct}%</span>
                  </div>
                  <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${b.status === 'critical' ? 'bg-red-500' : b.status === 'warning' ? 'bg-amber-500' : 'bg-emerald-500'}`}
                      style={{ width: `${Math.min(b.utilizationPct, 100)}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-gray-600 mt-0.5">
                    <span>${b.spent.toFixed(2)} spent</span>
                    <span>${b.amount.toFixed(2)} limit</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center text-gray-600 text-sm py-6">
              No budgets set.{' '}
              <Link to="/budget" className="text-indigo-400 hover:text-indigo-300 transition-colors">Create one</Link>
            </div>
          )}
        </div>
      </div>

      {/* Anomalies widget */}
      {anomalies && (anomalies.openCount > 0 || anomalies.resolvedCount > 0) && (
        <div className="card border-amber-800/50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-2xl">⚠️</span>
              <div>
                <h2 className="text-sm font-semibold text-white">Anomalies Detected</h2>
                <p className="text-xs text-gray-500">
                  {anomalies.openCount} open · {anomalies.resolvedCount} resolved (last 7 days)
                </p>
              </div>
            </div>
            <Link to="/anomalies" className="btn-secondary text-xs">Investigate →</Link>
          </div>
          {anomalies.recentAnomalies?.length > 0 && (
            <div className="mt-4 space-y-2">
              {anomalies.recentAnomalies.map((a) => (
                <div key={a.id} className="flex items-center justify-between p-2 bg-gray-800/40 rounded-lg">
                  <span className="text-xs text-gray-300 truncate flex-1">{a.description}</span>
                  <div className="flex items-center gap-2 ml-3 flex-shrink-0">
                    <StatusBadge status={a.severity} />
                    <StatusBadge status={a.status} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
