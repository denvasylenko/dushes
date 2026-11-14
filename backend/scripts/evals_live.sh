#!/usr/bin/env bash
# Live scenario evals against the running demo server (scripts/serve_demo.sh). The simulated user and the judge run
# here, so they need the Anthropic API key too: asked for when ANTHROPIC_API_KEY is not set, typed hidden, kept in
# this shell only (not written anywhere). Arguments go to scripts/evals.py, e.g.
#   bash backend/scripts/evals_live.sh --tag lab
#   bash backend/scripts/evals_live.sh lab_clinic_child stress_injection
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  printf 'Paste your Anthropic API key (sk-ant-..., hidden) and press Enter: '
  read -rs ANTHROPIC_API_KEY
  echo
fi
case "$ANTHROPIC_API_KEY" in
  sk-ant-*) ;;
  *) echo "That does not look like an Anthropic key (it starts with sk-ant-). Run the script again."; exit 1 ;;
esac
export ANTHROPIC_API_KEY
if ! curl -s -m 3 -o /dev/null http://127.0.0.1:8000/lab/map; then
  echo "The demo server is not running on :8000 (bash backend/scripts/serve_demo.sh)."; exit 1
fi
uv run python scripts/evals.py "$@" || true
uv run python scripts/eval_summary.py --out scripts/runs/summary-latest.md >/dev/null && echo "summary: scripts/runs/summary-latest.md"
