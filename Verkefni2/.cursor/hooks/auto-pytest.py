#!/usr/bin/env python3
"""Cursor postToolUse hook: run pytest after every agent edit and feed the
result back as additional context for the agent's next turn.

Wired up via `.cursor/hooks.json` with a matcher of `Write|StrReplace` so it
only fires after edit-style tool calls.
"""

import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VENV_PYTEST = PROJECT_ROOT / ".venv" / "bin" / "pytest"
PYTEST_TIMEOUT_SECONDS = 30


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
        payload = {
            "additional_context": (
                "auto-pytest hook: pytest is not installed. Run "
                "`pip install -r requirements.txt` to enable the auto "
                "feedback loop."
            )
        }
        print(json.dumps(payload))
        return
    except subprocess.TimeoutExpired:
        payload = {
            "additional_context": (
                f"auto-pytest hook: pytest timed out after "
                f"{PYTEST_TIMEOUT_SECONDS}s. Skipping this iteration."
            )
        }
        print(json.dumps(payload))
        return

    output = (result.stdout + result.stderr).strip() or "(no output)"
    payload = {
        "additional_context": (
            "--- auto-pytest result (this ran automatically after your "
            "last edit) ---\n"
            f"exit code: {result.returncode}\n"
            f"{output}"
        )
    }
    print(json.dumps(payload))


if __name__ == "__main__":
    main()
