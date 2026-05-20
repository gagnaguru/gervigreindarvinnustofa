---
name: fix-to-green
description: Procedural workflow for fixing failing pytest tests one at a time without modifying the test suite. Use when the user asks to fix failing tests, make tests pass, get to green, or work TDD-style on a Python project that already has a test suite.
---

# Fix to Green

When the user asks you to make failing tests pass, follow this exact
workflow. Do not skip steps. Do not batch fixes.

## Workflow

```
- [ ] 1. Run `pytest -q` to see the current state
- [ ] 2. Pick the FIRST failing test
- [ ] 3. Read the test source carefully — what behaviour does it require?
- [ ] 4. Read the matching production code — what does it currently do?
- [ ] 5. Form a one-sentence hypothesis: "the smallest change that would
        make this test pass is X"
- [ ] 6. Apply that change to the production code only
- [ ] 7. Run `pytest -q` again
- [ ] 8. If the chosen test now passes, repeat from step 2 with the next
        failure. If it still fails, revise your hypothesis.
```

Repeat until pytest reports zero failures.

## Hard rules

1. **Never edit a test to make it pass.** Tests are the contract. If a
   test seems wrong, stop and tell the user — do not silently change it.
2. **No `pytest.skip`, `xfail`, `pytest.mark.skip`, or `pytest.raises`
   wrappers added to tests** to dodge a failure. Same reasoning.
3. **No `try/except` in production code purely to swallow an assertion.**
   Fix the underlying logic instead.
4. **One failure at a time.** Do not change five things at once and hope
   the test count goes down. You will lose track of cause and effect.
5. **Rerun the whole suite after every fix.** A change that makes one
   test green can break another. The suite is the source of truth, not
   any single assertion.

## Reporting back to the user

After each iteration, briefly report:

- Which test you targeted
- What the test expected vs what the code did
- The minimal change you made
- The current pass / fail count

Keep this report to two or three lines per iteration. The user is
watching the loop, not reading an essay.

## When to stop and ask

Stop and ask the user before continuing if:

- A failing test contradicts another passing test
- A failing test contradicts the project spec (e.g. `PROJECT.md`)
- The "minimal change" would require rewriting a substantial part of
  the production module

In those cases the spec or the test is the bug, not the implementation,
and the user needs to decide.
