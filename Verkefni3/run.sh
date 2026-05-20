#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

MODEL="gpt-5.4-mini"

if [ -x ".venv/bin/python" ]; then
  PYTHON=".venv/bin/python"
else
  PYTHON="python3"
fi

# Start the dashboard SSE server in the background, kill it on exit.
"$PYTHON" eval/dashboard/sse_server.py >/tmp/skill-workshop-sse.log 2>&1 &
SSE_PID=$!
trap 'kill "$SSE_PID" 2>/dev/null || true' EXIT
sleep 0.5

if ! kill -0 "$SSE_PID" 2>/dev/null; then
  echo "SSE server failed to start. stderr:"
  tail -20 /tmp/skill-workshop-sse.log 2>/dev/null || true
  exit 1
fi

URL="http://127.0.0.1:8765/"
echo "Dashboard: $URL"
if command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL" >/dev/null 2>&1 || true
elif command -v open >/dev/null 2>&1; then open "$URL" >/dev/null 2>&1 || true
fi

"$PYTHON" eval/harness/run_harness.py --model "$MODEL" "$@"
