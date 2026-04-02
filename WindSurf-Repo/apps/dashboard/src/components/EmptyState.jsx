import React from 'react';

export default function EmptyState({ icon = '📭', title = 'No data', description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      <div className="text-4xl mb-3">{icon}</div>
      <h3 className="text-sm font-medium text-gray-300 mb-1">{title}</h3>
      {description && <p className="text-xs text-gray-500 max-w-sm">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
