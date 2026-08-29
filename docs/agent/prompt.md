# Agent prompt (user overrides)

Optional one-shot or standing instructions for the autonomous validation loop. **Read at the start of every cycle** (after `kb.md`). When this file is non-empty, treat its contents as **highest-priority user intent** for the current session, subject to anti-rig rules in the skill.

Leave blank when you have nothing to add.

---

**Standing (2026-08-29):** Always **PLAN → CRITIC subagent → RED tests → implement → pytest → JUDGE** before fit/generate/eval. Never skip critic/judge.

<!-- Append instructions below this line -->
