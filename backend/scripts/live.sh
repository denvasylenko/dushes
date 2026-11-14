#!/usr/bin/env bash
# Run live QA commands with the Anthropic API key, asked once (hidden, kept in this shell only, never written).
#   bash backend/scripts/live.sh "uv run python scripts/recipes.py" "uv run python scripts/landing_check.py"
# Each argument is one command, run from backend/ one after another; a failing command does not stop the others.
set -uo pipefail
cd "$(dirname "$0")/.."
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  printf 'Paste your Anthropic API key (sk-ant-..., hidden) and press Enter: '
  read -rs ANTHROPIC_API_KEY
  echo
fi
case "$ANTHROPIC_API_KEY" in
  sk-ant-*) ;;
  *) echo "That does not look like an Anthropic key (it starts with sk-ant-)."; exit 1 ;;
esac
export ANTHROPIC_API_KEY
for cmd in "$@"; do
  echo "=== $cmd"
  bash -c "$cmd" || echo "=== failed: $cmd"
done
echo "=== all done"
