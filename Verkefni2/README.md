# TDD Workshop — Phone Bill Calculator

A hands-on exercise (~25–30 min). You will build a small Python **billing
module** (several classes plus one convenience function) with an AI coding
agent, install a skill and a hook to give your agent TDD muscle memory,
generate tests, watch some fail, and iterate to green.

The goal is **not** to ship a perfect bill calculator. The goal is to
feel, in your own hands:

1. What tests catch that vibe coding misses.
2. What a small skill and a small hook do to your AI agent's
   behaviour in a tight inner loop.

## Choose your AI agent

This exercise works with **Cursor** and **Codex CLI** as first-class
options. Project orientation lives in [`AGENTS.md`](AGENTS.md), which
both read automatically. The step-2 helpers ship in two flavours, one
per tool.

### Cursor

1. Open the folder in Cursor.
2. Use the chat panel (Cmd/Ctrl-L) to send the prompts below.

### Codex CLI

1. Install once: `npm i -g @openai/codex`.
2. **One-time:** enable the hooks feature flag so your Codex CLI will
   load the auto-pytest hook in step 2. Append this to
   `~/.codex/config.toml` (create the file if it doesn't exist):

   ```toml
   [features]
   codex_hooks = true
   ```

3. From the project root, start a session: `codex`. The first time you
   run it here, Codex will ask whether to trust this project — say yes,
   otherwise hooks under `.codex/` won't load.
4. Paste the prompts below into the Codex prompt.

## Setup (do this before the workshop)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Verify pytest works (it should report "no tests ran" — that is fine):

```bash
pytest
```

## The flow

### 1. Read the spec — 2 min

Read [`PROJECT.md`](PROJECT.md). That is the only spec you get. Do **not**
look at `FACILITATOR.md` — it is the answer key.

### 2. Install the workshop helpers — 2 min

Two pre-built helpers live under [`workshop-extras/`](workshop-extras):
the `fix-to-green` skill and the `auto-pytest` hook. The skill body
is shared between the two tools; the hook ships in tool-specific
flavours under `cursor/` and `codex/`.

Run **one** of the install blocks below, matching the agent you chose.

#### If you're using Cursor

```bash
mkdir -p .cursor/hooks .cursor/skills
cp -r workshop-extras/skills/fix-to-green .cursor/skills/
cp workshop-extras/cursor/hooks/auto-pytest.py .cursor/hooks/
cp workshop-extras/cursor/hooks.json .cursor/hooks.json
chmod +x .cursor/hooks/auto-pytest.py
```

Cursor watches `hooks.json` and reloads on save, so the hook is live
immediately. The skill is loaded the next time you start a chat turn
that mentions failing tests.

#### If you're using Codex CLI

```bash
mkdir -p .agents/skills .codex/hooks
cp -r workshop-extras/skills/fix-to-green .agents/skills/
cp workshop-extras/codex/hooks/auto-pytest.py .codex/hooks/
cp workshop-extras/codex/hooks.json .codex/hooks.json
chmod +x .codex/hooks/auto-pytest.py
```

Then restart your `codex` session (or run `/skills` to refresh the
skill list). The skill auto-discovers from `.agents/skills/`. The hook
will only fire if you completed the one-time `[features] codex_hooks =
true` setup and trusted the project's `.codex/` layer — see the Codex
CLI section above.

#### What you just installed

- **`fix-to-green` skill** — when you later ask your agent to fix
  failing tests, the agent loads a procedural workflow: run pytest →
  pick the first failure → form a hypothesis → make the smallest
  possible change → re-run. It also enforces the cardinal rule:
  never edit a test to make it pass.
- **`auto-pytest` hook** — every time the agent writes or edits a file,
  pytest runs automatically and the result is fed back to the agent as
  context. You stop typing `pytest` by hand; the agent stops guessing
  whether its change worked.

The two flavours of the hook implement the same idea against the two
tools' schemas: Cursor wires it to `postToolUse` with `Write|StrReplace`,
Codex wires it to `PostToolUse` with `Edit|Write|apply_patch` and
returns its result inside the `hookSpecificOutput.additionalContext`
envelope. The Python script logic is the same in both.

### 3. Round 1 — vibe code the implementation — 5 min

Send your agent this prompt:

```
Read PROJECT.md and implement the billing model in billing.py: Plan,
Usage (including billable_voice_minutes), Bill, BillingCalculator, and
calculate_bill. Do not write any tests yet.
```

When the agent is done, glance over `billing.py`. It will probably look
correct. That is the trap.

### 4. Generate tests from the same spec — 3 min

Send this prompt:

```
Read PROJECT.md and write a thorough pytest suite in tests/test_billing.py.
Cover the happy path and every edge case implied by the spec — exact-quota
boundaries, zero usage, invalid input, fractional GB, VAT correctness,
voice billing (first full minute plus 30-second steps after that), and
behaviour of each public type (Plan, Usage, Bill, BillingCalculator).
Do not modify billing.py.
```

If the hook is installed, pytest will run automatically right after the
test file is written and the agent will see the failures. Otherwise,
run `pytest` yourself.

### 5. Look at the failures — 1 min

Most people see two to four failing tests. Do not panic — that is the
whole point of the exercise.

### 6. Round 2 — fix bugs TDD-style — 7 min

Send this prompt:

```
Fix the failing tests one at a time, TDD-style. Do not modify the tests.
```

Now watch the difference. With the skill loaded, the agent will:

- Run pytest, pick one failing test, read it, hypothesise, make a
  minimal change, re-run.
- Refuse if you nudge it toward editing the tests.

With the hook running, you do not need to type `pytest` between
iterations — the loop tightens itself.

### 7. Reflect — 2 min

- Which bugs did the tests catch that you would have shipped without
  them?
- Did the hook change how often you context-switched to your terminal?
- Did the skill change how the agent argued with itself when it got
  stuck?
- Which of these would you take back to your real projects?

## Reset between rounds

```bash
git checkout billing.py tests/test_billing.py
```

To uninstall the helpers (e.g. before doing the exercise a second time
without them, just to feel the difference):

```bash
# Cursor
rm -rf .cursor/hooks .cursor/skills .cursor/hooks.json

# Codex
rm -rf .codex .agents
```
