import React from 'react';

const STATUS_MAP = {
  healthy: { cls: 'badge-healthy', dot: 'bg-emerald-400', label: 'Healthy' },
  warning: { cls: 'badge-warning', dot: 'bg-amber-400', label: 'Warning' },
  critical: { cls: 'badge-critical', dot: 'bg-red-400', label: 'Critical' },
  unhealthy: { cls: 'badge-unhealthy', dot: 'bg-red-400', label: 'Unhealthy' },
  open: { cls: 'badge-critical', dot: 'bg-red-400', label: 'Open' },
  resolved: { cls: 'badge-healthy', dot: 'bg-emerald-400', label: 'Resolved' },
  low: { cls: 'badge-healthy', dot: 'bg-emerald-400', label: 'Low' },
  medium: { cls: 'badge-warning', dot: 'bg-amber-400', label: 'Medium' },
  high: { cls: 'badge-critical', dot: 'bg-red-400', label: 'High' },
  info: { cls: 'badge-info', dot: 'bg-blue-400', label: 'Info' },
};

export default function StatusBadge({ status, label, showDot = true }) {
  const s = STATUS_MAP[status?.toLowerCase()] || STATUS_MAP.info;
  return (
    <span className={s.cls}>
      {showDot && <span className={`w-1.5 h-1.5 rounded-full ${s.dot} inline-block`} />}
      {label || s.label}
    </span>
  );
}
