---
name: 21stdev
description: >-
  Connects to and uses the 21st.dev MCP (https://21st.dev/api/mcp) to search,
  inspect, and fetch UI components, themes, and templates. Use when the user
  says /21stdev, /21st, 21st.dev, Magic MCP, or asks to search/get a 21st
  component for AegisLoop or any UI task.
---

# /21stdev — 21st.dev MCP

Cursor loads this skill from `~/.cursor/skills/21stdev/` (personal) and `.cursor/skills/21stdev/` (project, gitignored). This copy is the repo backup.

## Do this first

1. Discover tools: `GetDynamicTools` with pattern `21st` or namespace that contains `21st`.
2. If the namespace is missing or `needsAuth`, enable **21st** in Cursor Settings → MCP. Do not invent component source.
3. Inspect the exact schema with `GetDynamicTools` (`namespace` + `toolName`) before `CallDynamicTool`.

Expected tools: `search`, `search_picker`, `get_component`, `get_theme`, `search_logo`. Prefer **search** then **get_component**.

## Auth (never commit)

- Endpoint: `https://21st.dev/api/mcp`
- Header: `x-api-key` (Bearer also works)
- Config: `~/.cursor/mcp.json` and/or project `.cursor/mcp.json`
- Optional env: `API_KEY_21ST`

## AegisLoop / GFF lock

Read [frontend/DESIGN.md](../../frontend/DESIGN.md) before installing anything.

**May steal:** dense tables, event/log rows, command palette structure, drawer-from-row.

**Must restyle** to paper/sage/ink + IBM Plex. Drop Inter, indigo, glass, `rounded-2xl`, shadows, looping motion, agent-chat chrome.

**Do not install:** shader/hero/testimonial/pricing blocks, AI-chat kits, neon SOC dashboards.
