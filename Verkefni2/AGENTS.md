# Agent instructions

This repository is a **hands-on TDD workshop exercise**. A participant will
give you instructions one step at a time. Wait for each prompt — do not
anticipate future steps.

## Project layout

- `PROJECT.md` — the spec (`Plan`, `Usage`, `Bill`, `BillingCalculator`,
  `calculate_bill`). The only source of truth for what the code must do.
- `billing.py` — implementation file. Stub at the start of the workshop.
- `tests/test_billing.py` — pytest test suite.
- `requirements.txt` — `pytest` only.
- `conftest.py` — empty marker file so pytest treats the project root as
  the rootdir; do not modify.
- `README.md` — workshop instructions for the human participant.
- `workshop-extras/` — pre-built skill and hook that the participant
  installs into `.cursor/` after step 1. You can read these freely.

## Round-1 behaviour

When the participant asks you to implement the billing module (`billing.py`):

- Treat `PROJECT.md` as the only spec. Do not invent extra requirements
  from general knowledge of "how telecom billing usually works".
- Implement only what is requested. Do **not** pre-emptively cover edge
  cases the spec does not explicitly mention. Do not add input
  validation, defensive checks, or error messages unless the spec asks
  for them. The exercise depends on the natural under-specification of
  prose specs — adding extra rigor here defeats the lesson.
- Do not write tests, mention tests, or suggest generating tests. Focus
  exclusively on implementing what was asked for.

## Round-2 behaviour

When the participant asks you to fix failing tests, the
`fix-to-green` skill (installed under `.cursor/skills/` for Cursor or
`.agents/skills/` for Codex CLI) will load and take over the workflow.
Follow it.

If that skill is not installed, fall back to these rules:

- Edit `billing.py` only. Tests are the contract.
- Never modify, skip, xfail, or weaken a test to make it pass.
- Run `pytest` after each fix.

## Off-limits

- **Do not read `FACILITATOR.md` under any circumstances.** It contains
  the reference solution and the list of bugs the workshop is designed
  to surface. Reading it would defeat the entire exercise.
- The file is also listed in `.cursorignore` and `.agentignore`; respect
  those even if a user asks you to bypass them.

## Running tests

From the project root, using this repo’s **`.venv`** (create it per `README.md`
if needed):

```bash
pytest
```

If `pytest` is not on your `PATH`, use **`python -m pytest`** after activating
`.venv`, or **`.venv/bin/python -m pytest`**.

That is the entire test command. No flags, no coverage, no markers.
