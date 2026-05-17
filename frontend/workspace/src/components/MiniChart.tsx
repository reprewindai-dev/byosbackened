export function MiniChart({ color = "text-brass-2", data }: { color?: string; data?: number[] }) {
  const points = data ?? Array.from({ length: 12 }, () => 10 + Math.random() * 20);
  const max = Math.max(...points);
  const h = 24;
  const w = 100;
  const d = points
    .map((p, i) => {
      const x = (i / (points.length - 1)) * w;
      const y = h - (p / max) * h;
      return `${i === 0 ? "M" : "L"} ${x} ${y}`;
    })
    .join(" ");

  const fillColor = color.includes("moss")
    ? "#5dd8a5"
    : color.includes("electric")
      ? "#6ea8fe"
      : color.includes("brass")
        ? "#e5b16e"
        : color.includes("amber")
          ? "#f0b340"
          : color.includes("violet")
            ? "#a78bfa"
            : "#c4925b";

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="h-6 w-full" preserveAspectRatio="none">
      <defs>
        <linearGradient id={`grad-${color}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={fillColor} stopOpacity="0.3" />
          <stop offset="100%" stopColor={fillColor} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`${d} L ${w} ${h} L 0 ${h} Z`} fill={`url(#grad-${color})`} />
      <path d={d} fill="none" stroke={fillColor} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
