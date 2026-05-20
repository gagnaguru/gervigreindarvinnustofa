#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "== TDD Workshop — setup =="

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

echo "  …verifying pytest"
.venv/bin/python -m pytest --version >/dev/null 2>&1
echo "  [OK]  pytest ready"

echo ""
echo "Setup complete. Open this folder in Cursor or start a Codex session."
