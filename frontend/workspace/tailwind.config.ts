import type { Config } from "tailwindcss";

// =============================================================
// VEKLOM DESIGN SYSTEM — Black + Brass/Orange
// LOCKED PALETTE — Do NOT add violet, purple, indigo, or any
// light-mode colors. This is a dark-only app.
// Accent hierarchy: brass (primary) → moss (success) → crimson (error) → amber (warn)
// =============================================================

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "#ffffff",
          1: "#f8fafc",
          2: "#f3f4f6",
          3: "#e5e7eb",
        },
        rule: {
          DEFAULT: "#e5e7eb",
          2: "#d1d5db",
        },
        bone: {
          DEFAULT: "#111827",
          2: "#374151",
        },
        muted: {
          DEFAULT: "#64748b",
          2: "#94a3b8",
        },
        brass: {
          DEFAULT: "#111827",
          2: "#334155",
        },
        moss: {
          DEFAULT: "#5dd8a5",
        },
        electric: {
          DEFAULT: "#6ea8fe",
        },
        amber: {
          DEFAULT: "#64748b",
        },
        crimson: {
          DEFAULT: "#ff6b6b",
        },
        // ❌ violet PERMANENTLY REMOVED — was leaking #a78bfa purple into UI
        // ❌ Do NOT re-add violet, purple, indigo, or any light-mode surface color
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      fontSize: {
        "2xs": ["10px", "14px"],
      },
      boxShadow: {
        soft: "0 1px 0 rgba(255,255,255,0.9) inset, 0 18px 45px -35px rgba(15,23,42,0.35)",
        "brass-glow": "0 0 0 rgba(0,0,0,0)",
        "moss-glow": "0 0 20px rgba(93,216,165,0.35)",
      },
      animation: {
        "pulse-soft": "pulse-soft 1.8s ease-in-out infinite",
        "fade-in": "fade-in 240ms ease-out",
      },
      keyframes: {
        "pulse-soft": {
          "0%, 100%": { opacity: "0.55", transform: "scale(1)" },
          "50%": { opacity: "1", transform: "scale(1.25)" },
        },
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
