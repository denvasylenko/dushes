#!/usr/bin/env bash
# Live scenario evals against the running demo server, then the round summary. The model key comes from the macOS
# keychain (see live.sh); arguments go to scripts/evals.py, e.g.
#   bash backend/scripts/evals_live.sh --tag lab
#   bash backend/scripts/evals_live.sh lab_clinic_child stress_injection
set -uo pipefail
cd "$(dirname "$0")/.."
if ! curl -s -m 3 -o /dev/null http://127.0.0.1:8000/lab/map; then
  echo "The demo server is not running on :8000 (bash backend/scripts/serve_demo.sh)."; exit 1
fi
args=""
for a in "$@"; do args="$args $(printf '%q' "$a")"; done
bash scripts/live.sh "uv run python scripts/evals.py$args" \
  "uv run python scripts/eval_summary.py --out scripts/runs/summary-latest.md > /dev/null && echo 'summary: scripts/runs/summary-latest.md'"
