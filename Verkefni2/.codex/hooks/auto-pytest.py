#!/usr/bin/env python3
"""Codex PostToolUse hook: run pytest after every agent edit and feed the
result back as additional developer context for the next turn.

Wired up via `.codex/hooks.json` with a matcher of `Edit|Write|apply_patch`
so it only fires after edit-style tool calls.

Codex hook contract:
- Reads a JSON object from stdin
- Writes a JSON object to stdout with the shape:
    {
      "hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": "<text the model will see>"
      }
    }
"""

import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VENV_PYTEST = PROJECT_ROOT / ".venv" / "bin" / "pytest"
PYTEST_TIMEOUT_SECONDS = 30


def emit(text: str) -> None:
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": text,
        }
    }
    print(json.dumps(payload))


def main() -> None:
    try:
        json.load(sys.stdin)
    except json.JSONDecodeError:
        return

    try:
        result = subprocess.run(
            [str(VENV_PYTEST) if VENV_PYTEST.exists() else "pytest",
             "-q", "--tb=short", "--no-header"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=PYTEST_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        emit(
            "auto-pytest hook: pytest is not installed. Run "
            "`pip install -r requirements.txt` to enable the auto "
            "feedback loop."
        )
        return
    except subprocess.TimeoutExpired:
        emit(
            f"auto-pytest hook: pytest timed out after "
            f"{PYTEST_TIMEOUT_SECONDS}s. Skipping this iteration."
        )
        return

    output = (result.stdout + result.stderr).strip() or "(no output)"
    emit(
        "--- auto-pytest result (this ran automatically after your "
        "last edit) ---\n"
        f"exit code: {result.returncode}\n"
        f"{output}"
    )


if __name__ == "__main__":
    main()
