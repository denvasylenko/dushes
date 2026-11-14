#!/usr/bin/env bash
# Run live QA commands with the model keys from the macOS keychain (company rule: keys live only there, never in
# files, git, logs or reports). Each argument is one command, run from backend/ one after another; a failing command
# does not stop the others.
#   bash backend/scripts/live.sh "uv run python scripts/recipes.py" "uv run python scripts/landing_check.py"
#   LIVE_OPENAI=1 bash backend/scripts/live.sh "uv run python scripts/evals.py --agent-model openai:<model> ..."
# Entries: herefront-claude-live (Anthropic, always) and herefront-openai-live (OpenAI, with LIVE_OPENAI=1). A key
# already in the environment is used as it is. The script never asks for a key and never prints one.
set -uo pipefail
cd "$(dirname "$0")/.."

key() {   # key <ENV_NAME> <keychain entry>: the variable from the environment, else from the keychain
  local name="$1" entry="$2" value="${!1:-}"
  if [ -z "$value" ]; then
    value="$(security find-generic-password -a "$USER" -s "$entry" -w 2>/dev/null || true)"
  fi
  if [ -z "$value" ]; then
    echo "No key: the keychain has no entry \"$entry\". Add it yourself (the key is typed hidden):"
    echo "  security add-generic-password -a \"\$USER\" -s $entry -w"
    exit 1
  fi
  export "$name=$value"
}

key ANTHROPIC_API_KEY herefront-claude-live
if [ "${LIVE_OPENAI:-}" = "1" ]; then key OPENAI_API_KEY herefront-openai-live; fi
for cmd in "$@"; do
  echo "=== $cmd"
  bash -c "$cmd" || echo "=== failed: $cmd"
done
echo "=== all done"
