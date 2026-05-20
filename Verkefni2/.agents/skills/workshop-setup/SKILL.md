---
name: workshop-setup
description: >-
  Copy the pre-built test suite into tests/test_billing.py and run pytest.
  All other helpers (fix-to-green skill, auto-pytest hook) are already
  pre-installed. Use when the user says "setup tests", "set up tests",
  "set up workshop", "install helpers", "add tests", or "run tests" when
  no tests exist.
---

# Workshop Setup

The fix-to-green skill and auto-pytest hook are already pre-installed
in this repository. This skill only needs to copy the test suite.

**IMPORTANT: After running these commands, report results and STOP.
Do not fix any failing tests. Wait for the user's next prompt.**

## Commands

Run from the project root:

```bash
cp workshop-extras/tests/test_billing.py tests/test_billing.py
```

## Verify

Run `pytest` to confirm the tests are in place. Report the pass/fail
count to the user.

**Then stop. Do not attempt to fix any failures. The user will give
you the next instruction.**
