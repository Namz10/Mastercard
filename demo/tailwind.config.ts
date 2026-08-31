import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "var(--bg)",
        foreground: "var(--ink)",
        primary: {
          DEFAULT: "var(--accent)",
          foreground: "var(--accent-fg)",
        },
        secondary: {
          DEFAULT: "var(--canvas)",
          foreground: "var(--ink-muted)",
        },
        muted: {
          DEFAULT: "var(--canvas)",
          foreground: "var(--ink-faint)",
        },
        accent: {
          DEFAULT: "var(--accent)",
          hover: "var(--accent-hover)",
          muted: "var(--accent-muted)",
          fg: "var(--accent-fg)",
          foreground: "var(--accent-fg)",
        },
        card: {
          DEFAULT: "var(--surface-solid)",
          foreground: "var(--ink)",
        },
        destructive: {
          DEFAULT: "var(--signal-block)",
          foreground: "var(--paper-1)",
        },
        border: "var(--border)",
        input: "var(--border)",
        ring: "var(--accent)",
        bg: "var(--bg)",
        canvas: "var(--canvas)",
        surface: "var(--surface)",
        "surface-solid": "var(--surface-solid)",
        "surface-float": "var(--surface-float)",
        "surface-sunken": "var(--surface-sunken)",
        "border-strong": "var(--border-strong)",
        ink: "var(--ink)",
        "ink-muted": "var(--ink-muted)",
        "ink-faint": "var(--ink-faint)",
        paper: {
          0: "var(--paper-0)",
          1: "var(--paper-1)",
        },
        sage: {
          100: "var(--sage-100)",
          600: "var(--sage-600)",
          700: "var(--sage-700)",
        },
        ochre: {
          700: "var(--ochre-700)",
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
        sheet: "var(--radius-sheet)",
        bento: "var(--radius-bento)",
      },
      boxShadow: {
        drawer: "var(--shadow-drawer)",
        float: "var(--shadow-float)",
        bento: "var(--shadow-bento)",
      },
    },
  },
  plugins: [],
} satisfies Config;
