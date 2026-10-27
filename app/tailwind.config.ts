import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["Fraunces", "Georgia", "serif"],
        sans: ["IBM Plex Sans", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
      colors: {
        bg: "hsl(var(--bg))",
        panel: "hsl(var(--panel))",
        line: "hsl(var(--line))",
        ink: "hsl(var(--ink))",
        muted: "hsl(var(--muted))",
        accent: { DEFAULT: "hsl(var(--accent))", soft: "hsl(var(--accent-soft))" },
        good: { DEFAULT: "hsl(var(--good))", soft: "hsl(var(--good-soft))" },
        bad: { DEFAULT: "hsl(var(--bad))", soft: "hsl(var(--bad-soft))" },
        warn: { DEFAULT: "hsl(var(--warn))", soft: "hsl(var(--warn-soft))" },
      },
      keyframes: {
        rise: { from: { opacity: "0", transform: "translateY(8px)" }, to: { opacity: "1", transform: "none" } },
        pulseRing: { "0%": { boxShadow: "0 0 0 0 hsl(var(--bad) / .45)" }, "100%": { boxShadow: "0 0 0 14px hsl(var(--bad) / 0)" } },
      },
      animation: { rise: "rise .45s ease-out both", pulseRing: "pulseRing 1.1s ease-out 1" },
    },
  },
  plugins: [],
} satisfies Config;
