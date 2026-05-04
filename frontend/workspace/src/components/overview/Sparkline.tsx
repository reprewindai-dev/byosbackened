interface SparklineProps {
  values: number[];
  width?: number;
  height?: number;
  stroke?: string;
  fill?: string;
  strokeWidth?: number;
  showFill?: boolean;
}

/**
 * Tiny inline sparkline. Smooth curve via mid-point quadratic interpolation.
 * If `values` is empty or all-zero, renders a flat baseline so the card still
 * has the right visual weight without faking activity.
 */
export function Sparkline({
  values,
  width = 200,
  height = 36,
  stroke = "rgba(229, 177, 110, 0.95)", // brass-2
  fill = "rgba(229, 177, 110, 0.18)",
  strokeWidth = 1.5,
  showFill = true,
}: SparklineProps) {
  if (!values || values.length === 0) {
    return (
      <svg viewBox={`0 0 ${width} ${height}`} className="h-full w-full" preserveAspectRatio="none">
        <line
          x1={0}
          y1={height - 2}
          x2={width}
          y2={height - 2}
          stroke="rgba(229, 177, 110, 0.25)"
          strokeWidth={1}
          strokeDasharray="2 3"
        />
      </svg>
    );
  }

  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = max - min || 1;
  const padY = 3;

  const points = values.map((v, i) => {
    const x = (i / Math.max(1, values.length - 1)) * width;
    const y = height - padY - ((v - min) / range) * (height - padY * 2);
    return { x, y };
  });

  // Mid-point quadratic smoothing.
  let path = `M ${points[0].x.toFixed(2)} ${points[0].y.toFixed(2)}`;
  for (let i = 1; i < points.length; i++) {
    const prev = points[i - 1];
    const cur = points[i];
    const midX = (prev.x + cur.x) / 2;
    const midY = (prev.y + cur.y) / 2;
    path += ` Q ${prev.x.toFixed(2)} ${prev.y.toFixed(2)}, ${midX.toFixed(2)} ${midY.toFixed(2)}`;
  }
  const last = points[points.length - 1];
  path += ` T ${last.x.toFixed(2)} ${last.y.toFixed(2)}`;

  const fillPath = `${path} L ${last.x.toFixed(2)} ${height} L ${points[0].x.toFixed(2)} ${height} Z`;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-full w-full" preserveAspectRatio="none">
      {showFill && <path d={fillPath} fill={fill} />}
      <path
        d={path}
        fill="none"
        stroke={stroke}
        strokeWidth={strokeWidth}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}
