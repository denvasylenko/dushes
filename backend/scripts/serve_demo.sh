#!/usr/bin/env bash
# Start the demo server. Asks for the Anthropic API key when ANTHROPIC_API_KEY is not set; the typing is hidden
# and the key stays in this shell only (it is not written anywhere).
#   bash backend/scripts/serve_demo.sh            # http://localhost:8000
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
if lsof -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port 8000 is taken: stop the other server first (Ctrl-C in its tab)."; exit 1
fi
exec uv run uvicorn demo.app:app --port 8000 --reload --reload-dir formguide --reload-dir demo
