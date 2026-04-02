import React from 'react';
import LoadingSpinner from './LoadingSpinner';
import EmptyState from './EmptyState';

export default function DataTable({ columns, rows, loading, emptyIcon, emptyTitle, emptyDesc, keyField = 'id' }) {
  if (loading) return <LoadingSpinner centered />;
  if (!rows || rows.length === 0) {
    return <EmptyState icon={emptyIcon || '📋'} title={emptyTitle || 'No records'} description={emptyDesc} />;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-800">
            {columns.map((col) => (
              <th key={col.key} className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide whitespace-nowrap">
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-800/60">
          {rows.map((row) => (
            <tr key={row[keyField]} className="hover:bg-gray-800/40 transition-colors">
              {columns.map((col) => (
                <td key={col.key} className="px-4 py-3 text-gray-300 whitespace-nowrap">
                  {col.render ? col.render(row[col.key], row) : row[col.key] ?? '—'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
