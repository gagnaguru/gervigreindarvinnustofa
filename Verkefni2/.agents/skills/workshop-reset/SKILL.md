---
name: workshop-reset
description: >-
  Reset the workshop to its starting state. Reverts billing.py to stubs
  and tests/test_billing.py to empty. Use when the user says "reset",
  "start over", "clean slate", or "reset the workshop".
---

# Workshop Reset

Revert the repository to its starting state so the workshop can be
run again from scratch.

## Commands

Run from the project root:

```bash
git checkout billing.py tests/test_billing.py
```

This restores:
- `billing.py` — back to stubs (all `NotImplementedError`)
- `tests/test_billing.py` — back to empty

## What is preserved

- Installed helpers (`.cursor/skills/`, `.cursor/hooks/`, or
  `.agents/`, `.codex/`) are gitignored and survive the reset.
- `PROJECT.md`, `AGENTS.md`, `README.md` — unchanged.
- `FACILITATOR.md` — untouched (untracked, not affected by checkout).

## After reset

Tell the user the workspace is clean and ready for a fresh run.
Do not start implementing or generating tests — wait for the user's
next prompt.
