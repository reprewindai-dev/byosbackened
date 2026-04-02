import React, { useState, useEffect, useCallback } from 'react';
import { insightsApi } from '../utils/api';
import PageHeader from '../components/PageHeader';
import MetricCard from '../components/MetricCard';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

export default function Insights() {
  const [savings, setSavings] = useState(null);
  const [projected, setProjected] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [months, setMonths] = useState(3);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [savRes, projRes, sugRes] = await Promise.all([
        insightsApi.getSavings(),
        insightsApi.getProjected(months),
        insightsApi.getSuggestions().catch(() => ({ data: { suggestions: [] } })),
      ]);
      setSavings(savRes.data);
      setProjected(projRes.data);
      setSuggestions(sugRes.data.suggestions || []);
    } catch { /* silent */ } finally {
      setLoading(false);
    }
  }, [months]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <LoadingSpinner centered />;

  const fmtMoney = (v) => `$${Number(v || 0).toFixed(2)}`;

  return (
    <div className="space-y-6 max-w-5xl">
      <PageHeader
        title="Savings Insights"
        description="See exactly how much BYOS saves you vs. paying retail AI prices"
        actions={
          <div className="flex gap-1">
            {[1, 3, 6, 12].map((m) => (
              <button key={m} onClick={() => setMonths(m)}
                className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${months === m ? 'bg-indigo-600 text-white' : 'btn-secondary'}`}>
                {m}mo
              </button>
            ))}
          </div>
        }
      />

      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard title="Total Saved" value={fmtMoney(savings?.total_savings)} subtitle="vs. retail pricing" icon="💸" color="emerald" />
        <MetricCard title="Baseline Cost" value={fmtMoney(savings?.baseline_cost)} subtitle="what you would've paid" icon="📈" color="red" />
        <MetricCard title="Actual Cost" value={fmtMoney(savings?.actual_cost)} subtitle="what you paid via BYOS" icon="📉" color="blue" />
        <MetricCard title="Savings %" value={`${Number(savings?.savings_percent || 0).toFixed(1)}%`} subtitle="efficiency gain" icon="🏆" color="indigo" />
      </div>

      {/* Projected savings */}
      {projected && (
        <div className="card">
          <h2 className="text-sm font-semibold text-white mb-4">Projected Savings ({months} months)</h2>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="p-4 bg-emerald-900/20 border border-emerald-800 rounded-lg">
              <div className="text-xs text-emerald-500 mb-1">Projected Savings</div>
              <div className="text-2xl font-bold text-emerald-400">{fmtMoney(projected.projected_savings)}</div>
              <div className="text-xs text-emerald-600 mt-1">{Number(projected.projected_savings_percent || 0).toFixed(1)}% savings rate</div>
            </div>
            <div className="p-4 bg-gray-800/60 rounded-lg">
              <div className="text-xs text-gray-500 mb-1">Monthly Average Saved</div>
              <div className="text-2xl font-bold text-white">{fmtMoney(projected.monthly_avg_savings)}</div>
              <div className="text-xs text-gray-600 mt-1">based on historical data</div>
            </div>
            <div className="p-4 bg-indigo-900/20 border border-indigo-800 rounded-lg">
              <div className="text-xs text-indigo-500 mb-1">Annual Projection</div>
              <div className="text-2xl font-bold text-indigo-400">{fmtMoney((projected.monthly_avg_savings || 0) * 12)}</div>
              <div className="text-xs text-indigo-600 mt-1">extrapolated 12 months</div>
            </div>
          </div>
        </div>
      )}

      {/* Savings history chart */}
      {savings?.operations_count > 0 && (
        <div className="card">
          <h2 className="text-sm font-semibold text-white mb-2">Operations Summary</h2>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mt-4">
            <div>
              <div className="text-xs text-gray-500">Total Operations</div>
              <div className="text-lg font-semibold text-white">{Number(savings.operations_count || 0).toLocaleString()}</div>
            </div>
            {savings.latency_reduction_ms && (
              <div>
                <div className="text-xs text-gray-500">Latency Reduction</div>
                <div className="text-lg font-semibold text-emerald-400">{savings.latency_reduction_ms}ms</div>
              </div>
            )}
            {savings.cache_hit_rate_improvement && (
              <div>
                <div className="text-xs text-gray-500">Cache Hit Improvement</div>
                <div className="text-lg font-semibold text-blue-400">{(savings.cache_hit_rate_improvement * 100).toFixed(1)}%</div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Suggestions */}
      <div className="card">
        <h2 className="text-sm font-semibold text-white mb-4">Optimization Suggestions</h2>
        {suggestions.length === 0 ? (
          <EmptyState
            icon="💡"
            title="No suggestions yet"
            description="As your usage grows, BYOS will generate specific optimization recommendations"
          />
        ) : (
          <div className="space-y-3">
            {suggestions.map((s, i) => (
              <div key={i} className="flex items-start gap-3 p-3 bg-gray-800/40 rounded-lg">
                <span className="text-xl flex-shrink-0">
                  {s.priority === 'high' ? '🔴' : s.priority === 'medium' ? '🟡' : '🟢'}
                </span>
                <div>
                  <div className="text-sm font-medium text-white">{s.title || s.suggestion}</div>
                  {s.description && <div className="text-xs text-gray-500 mt-0.5">{s.description}</div>}
                  {s.estimated_savings && (
                    <div className="text-xs text-emerald-400 mt-1">
                      Est. savings: {fmtMoney(s.estimated_savings)}/mo
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* No data state */}
      {!savings?.operations_count && (
        <div className="card text-center py-12">
          <div className="text-4xl mb-3">🚀</div>
          <h3 className="text-sm font-medium text-gray-300 mb-1">Start saving money with BYOS</h3>
          <p className="text-xs text-gray-500 max-w-sm mx-auto">
            Route AI operations through BYOS to start tracking cost savings vs. retail pricing.
            Savings are calculated automatically from your audit logs.
          </p>
        </div>
      )}
    </div>
  );
}
