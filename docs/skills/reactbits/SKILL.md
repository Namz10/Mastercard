---
name: reactbits
description: >-
  Uses the shadcn MCP plus the @react-bits registry to browse, search, and
  install React Bits components. Use when the user says /reactbits, React Bits,
  reactbits.dev, Dither, FadeContent, or asks to pull an animated React
  component from that registry.
---

# /reactbits — React Bits via shadcn MCP

Cursor loads this skill from `~/.cursor/skills/reactbits/` and `.cursor/skills/reactbits/`. This copy is the repo backup.

## Cursor vs Claude Code (do not mix)

This repo is **Cursor**. React Bits’ MCP page defaults to `--client claude` (writes `.mcp.json`). Official Cursor init is `npx shadcn@latest mcp init --client cursor`. **Do not run `--client claude`.** Naive Cursor init also omits `--cwd frontend`, so `@react-bits` is invisible. Project `.cursor/mcp.json` already runs `npx -y shadcn@latest mcp --cwd <repo>/frontend`. If tools are missing: Cursor Settings → MCP → enable **shadcn**.

## Do this first

1. Confirm [frontend/components.json](../../frontend/components.json) has `@react-bits`.
2. Discover tools: `GetDynamicTools` with pattern `shadcn` or `react-bits`.
3. Enable **shadcn** in Cursor Settings → MCP if missing. It must run with `--cwd frontend`.
4. Prefer TypeScript + Tailwind installs:

```bash
npx shadcn@latest add @react-bits/FadeContent-TS-TW --cwd frontend
```

## Motion law

Almost the entire React Bits catalog is **banned** on the GFF booth UI.

**Allowed (restyle + `prefers-reduced-motion`):** FadeContent / AnimatedContent (one-shot 80–160ms); CountUp (final number instantly if reduced motion).

**Maybe (usually skip):** Counter; Stepper.

**Forbidden:** Dither, ClickSpark, ElectricBorder, GlitchText, GradientText, ParticleText, BlobCursor, Cubes, ASCII/Decrypted/Shiny text, all shader Backgrounds, bounce/physics, glass, marquees.

See [frontend/DESIGN.md](../../frontend/DESIGN.md) §12.
