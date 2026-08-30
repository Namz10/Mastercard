import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        surface: "var(--surface)",
        "surface-sunken": "var(--surface-sunken)",
        border: "var(--border)",
        "border-strong": "var(--border-strong)",
        ink: "var(--ink)",
        "ink-muted": "var(--ink-muted)",
        "ink-faint": "var(--ink-faint)",
        paper: {
          0: "var(--paper-0)",
          1: "var(--paper-1)",
        },
        slate: {
          600: "var(--slate-600)",
        },
        signal: {
          block: "var(--signal-block)",
          watch: "var(--signal-watch)",
          safe: "var(--signal-safe)",
          idle: "var(--signal-idle)",
          info: "var(--signal-info)",
        },
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "system-ui", "sans-serif"],
        serif: ["IBM Plex Serif", "Georgia", "serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
      borderRadius: {
        DEFAULT: "var(--radius)",
        sm: "var(--radius-sm)",
        drawer: "var(--radius-drawer)",
      },
      boxShadow: {
        drawer: "var(--shadow-drawer)",
      },
    },
  },
  plugins: [],
} satisfies Config;
