import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "#070810",
          1: "#0b0d16",
          2: "#10131e",
          3: "#161a28",
        },
        rule: {
          DEFAULT: "#1e2230",
          2: "#272c3e",
        },
        bone: {
          DEFAULT: "#f4f2ed",
          2: "#c8cbd6",
        },
        muted: {
          DEFAULT: "#7b849a",
          2: "#566077",
        },
        brass: {
          DEFAULT: "#c4925b",
          2: "#e5b16e",
        },
        moss: {
          DEFAULT: "#5dd8a5",
        },
        electric: {
          DEFAULT: "#6ea8fe",
        },
        amber: {
          DEFAULT: "#f0b340",
        },
        crimson: {
          DEFAULT: "#ff6b6b",
        },
        violet: {
          DEFAULT: "#a78bfa",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      fontSize: {
        "2xs": ["10px", "14px"],
      },
      boxShadow: {
        soft: "0 1px 0 rgba(255,255,255,0.03) inset, 0 20px 60px -20px rgba(0,0,0,0.8)",
        "brass-glow": "0 0 20px rgba(229,177,110,0.35)",
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
