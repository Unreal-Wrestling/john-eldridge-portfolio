---
description: Produce a context handoff summary so a long chat can be restarted in a fresh conversation without losing state
---

# Handoff Summary

Run this when a conversation is getting long and risks a "request entity too large" failure,
or any time the user types `/handoff`.

## When Cascade should offer this WITHOUT being asked

Proactively offer a handoff (one short line, do not nag) as soon as ANY of these are true:

- 20+ exchanges have occurred in this conversation.
- 10+ distinct files have been read into context.
- A single tool call returned more than ~500 lines (full-file read, `git log`, full `build.py` output, a long contact sheet).
- A `code_search` has been run 3+ times.
- The user reports slow responses or a truncated reply.

Offer format, verbatim, so it is easy to ignore:
> Context is getting heavy. Say `/handoff` and I'll write a restart summary.

## Producing the summary

Output a fenced code block the user can copy into a NEW chat. Keep it under 40 lines.
It MUST contain, in this order:

1. **Goal** — one sentence: what we are actually trying to accomplish.
2. **Workspace** — branch (`master`), and whether there are uncommitted changes or an undeployed build.
3. **Done** — bullets of what has already shipped, with commit SHAs where they exist.
4. **In progress** — the single current step, and exactly where it stopped.
5. **Next** — the ordered remaining steps.
6. **Key files** — absolute paths with line ranges, citation format. No prose descriptions.
7. **Decisions/constraints** — anything John ruled in or out that is NOT already a saved memory.
8. **Gotchas** — failures already hit, so the next session does not repeat them.

## Rules

- Do NOT re-read files just to write the summary. Use what is already in context.
- Do NOT restate anything already captured in a persistent memory. Reference it instead.
- If a fact discovered this session is durable and project-wide, save it as a memory
  instead of putting it in the handoff (handoffs are disposable, memories are not).
- Never include secrets or tokens.
- After emitting the summary, stop. Do not continue working in the old chat.
- If a change was made but not yet shipped, say so explicitly — default for this repo is
  straight to production (see `deploy_portfolio`), so an unshipped change is an open loop.

## Habits that prevent needing this

- One conversation per project write-up or feature.
- Ask for specific line ranges instead of whole files.
- Prefer `grep_search` / `code_search` over reading files end to end.
- `project.md` files are small — reading those is cheap. `build.py`, `work.css`, and
  `index.html` are not; cite line ranges.
- Pipe noisy commands through a limit (`git log -n 10`).
