#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "== Skill Workshop — setup =="

if ! command -v python3 >/dev/null 2>&1; then
  echo "[RED] python3 not found." && exit 2
fi
py_ver=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
echo "  [OK]  python3 ($py_ver)"

if [ ! -d ".venv" ]; then
  echo "  …creating .venv"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
echo "  [OK]  python deps installed"

if ! command -v codex >/dev/null 2>&1; then
  echo "[RED] codex CLI not found. Install: https://developers.openai.com/codex/cli/install" && exit 2
fi
echo "  [OK]  codex CLI on PATH"

if [ -z "${OPENAI_API_KEY:-}" ]; then
  if codex login status >/dev/null 2>&1; then
    echo "  [OK]  codex authenticated (login)"
  else
    echo "[RED] no OPENAI_API_KEY and codex not logged in. Run 'codex login' or set OPENAI_API_KEY." && exit 2
  fi
else
  echo "  [OK]  OPENAI_API_KEY set"
fi

python eval/harness/setup_check.py
