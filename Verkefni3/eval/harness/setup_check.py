"""Pre-flight: prove that `codex exec` runs end-to-end on this machine.

Exit 0 = green. Non-zero = red with a one-line diagnostic.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from codex_runner import run_codex_battle  # noqa: E402

ROOT = Path(__file__).parent.parent          # eval/
PROJECT_ROOT = ROOT.parent / "battle-prediction-agent"


def main() -> int:
    print("Pre-flight check…")

    if not shutil.which("codex"):
        print("  [RED] codex CLI not found on PATH.")
        print("        Install: https://developers.openai.com/codex/cli/install")
        return 2
    print("  [OK]  codex CLI on PATH")

    example = ROOT / "data" / "examples" / "01_charizard_blastoise.txt"
    if not example.exists():
        print(f"  [RED] missing example file: {example}")
        return 2

    with tempfile.TemporaryDirectory(prefix="codex_warmup_") as tmp:
        tmp_path = Path(tmp)
        for name in ("AGENTS.md",):
            src = PROJECT_ROOT / name
            if src.exists():
                shutil.copy2(src, tmp_path / name)
        src_skills = PROJECT_ROOT / ".agents"
        if src_skills.exists():
            shutil.copytree(src_skills, tmp_path / ".agents", dirs_exist_ok=True)

        doc = example.read_text(encoding="utf-8")
        print("  …running one warm-up prediction (this may take ~30–60s)")
        run = run_codex_battle(doc, tmp_path, timeout=180)

    if run.error or run.exit_code != 0:
        print(f"  [RED] codex exec failed: {run.error or 'unknown error'}")
        if run.stderr_tail:
            print("        stderr tail:")
            for line in run.stderr_tail.splitlines()[-8:]:
                print(f"          {line}")
        return 3

    if not run.raw_output.strip():
        print("  [RED] codex exec returned no final message.")
        return 4

    if run.total_tokens == 0:
        print("  [WARN] no token usage observed — token-efficiency axis will be skipped.")
    else:
        print(f"  [OK]  token usage observed ({run.total_tokens} total)")

    print(f"  [OK]  final message length: {len(run.raw_output)} chars")
    print(f"  [OK]  latency: {run.latency_sec:.1f}s")
    print()
    print("GREEN — you are ready. Run `./run.sh` (or `./run.ps1` on Windows) to begin.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
