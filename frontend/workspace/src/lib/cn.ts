import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export function fmtCents(cents: number, currency: string = "USD"): string {
  const amount = cents / 100;
  try {
    return amount.toLocaleString(undefined, {
      style: "currency",
      currency: currency.toUpperCase(),
      minimumFractionDigits: 2,
    });
  } catch {
    return `${amount.toFixed(2)} ${currency.toUpperCase()}`;
  }
}

export function fmtNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(n >= 10_000 ? 0 : 1)}k`;
  return n.toLocaleString();
}

export function fmtDelta(n: number, suffix = ""): string {
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(n % 1 === 0 ? 0 : 1)}${suffix}`;
}

export function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const rawDiff = Date.now() - then;
  const future = rawDiff < 0;
  const diff = Math.abs(rawDiff);
  const s = Math.floor(diff / 1000);
  const prefix = future ? "in " : "";
  const suffix = future ? "" : " ago";
  if (s < 60) return `${prefix}${s}s${suffix}`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${prefix}${m}m${suffix}`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${prefix}${h}h${suffix}`;
  const d = Math.floor(h / 24);
  if (d < 7) return `${prefix}${d}d${suffix}`;
  return new Date(iso).toLocaleDateString();
}
