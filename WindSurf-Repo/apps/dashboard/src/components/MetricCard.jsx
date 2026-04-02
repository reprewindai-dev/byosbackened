import React from 'react';
import clsx from 'clsx';

export default function MetricCard({ title, value, subtitle, icon, trend, trendLabel, color = 'indigo', loading = false }) {
  const colorMap = {
    indigo: 'text-indigo-400 bg-indigo-900/30',
    emerald: 'text-emerald-400 bg-emerald-900/30',
    amber: 'text-amber-400 bg-amber-900/30',
    red: 'text-red-400 bg-red-900/30',
    blue: 'text-blue-400 bg-blue-900/30',
    purple: 'text-purple-400 bg-purple-900/30',
  };
  const iconCls = colorMap[color] || colorMap.indigo;

  if (loading) {
    return (
      <div className="card animate-pulse">
        <div className="flex items-start justify-between">
          <div className="space-y-2 flex-1">
            <div className="h-3 bg-gray-800 rounded w-24" />
            <div className="h-7 bg-gray-800 rounded w-16" />
            <div className="h-3 bg-gray-800 rounded w-32" />
          </div>
          <div className="w-10 h-10 rounded-lg bg-gray-800" />
        </div>
      </div>
    );
  }

  return (
    <div className="card hover:border-gray-700 transition-colors">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">{title}</p>
          <p className="text-2xl font-bold text-white truncate">{value}</p>
          {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
          {trend !== undefined && (
            <div className="flex items-center gap-1 mt-2">
              <span className={clsx('text-xs font-medium', trend >= 0 ? 'text-emerald-400' : 'text-red-400')}>
                {trend >= 0 ? '▲' : '▼'} {Math.abs(trend)}%
              </span>
              {trendLabel && <span className="text-xs text-gray-600">{trendLabel}</span>}
            </div>
          )}
        </div>
        {icon && (
          <div className={clsx('w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ml-3', iconCls)}>
            <span className="text-lg">{icon}</span>
          </div>
        )}
      </div>
    </div>
  );
}
