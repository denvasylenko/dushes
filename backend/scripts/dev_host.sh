#!/usr/bin/env bash
# The owner's local dev host: the public host (docs site, Ask AI, the demo pages, the researcher) on localhost,
# built from what is COMMITTED on main and rebuilt whenever main moves. It runs from its own checkout
# (.claude/worktrees/dev-host, git-excluded), never from the shared folder, so nobody's uncommitted work shows up.
#
# Start (from the repository root; the keys come from the macOS keychain through live.sh, which never prints one):
#   LIVE_OPENAI=1 bash backend/scripts/live.sh "bash scripts/dev_host.sh"
# Then open http://localhost:8190/ . Stop with Ctrl-C. The same command restarts it.
#
#   DEV_HOST_PORT   the port (8190)          DEV_HOST_REF   what to follow (main)
#   DEV_HOST_EVERY  seconds between looks at the ref (20)
# The money limits are the public ones ($3 Haiku + $2 Luna a day). The message limits are higher here, so that
# testing does not stop at ten messages (the CPO, 2026-11-15): 200 a visitor and 400 an address a day, 100 in one
# conversation. Any DEMO_*
# variable set before the start wins (docs_ai/host.py).
set -uo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
WT="$REPO/.claude/worktrees/dev-host"
PORT="${DEV_HOST_PORT:-8190}"
REF="${DEV_HOST_REF:-main}"
EVERY="${DEV_HOST_EVERY:-20}"
SERVER=""
export DEMO_PER_VISITOR_DAY="${DEMO_PER_VISITOR_DAY:-200}" DEMO_PER_IP_DAY="${DEMO_PER_IP_DAY:-400}" DEMO_PER_THREAD="${DEMO_PER_THREAD:-100}"

say() { echo "[dev-host $(date +%H:%M:%S)] $*"; }

# npm ci only when a lock file changed since the last install in this checkout
deps() {   # deps <dir>
  local dir="$1" stamp="$WT/$1/node_modules/.dev-host-lock"
  local now; now="$(shasum "$WT/$dir/package-lock.json" | cut -d' ' -f1)"
  if [ ! -f "$stamp" ] || [ "$(cat "$stamp")" != "$now" ]; then
    say "installing $dir"
    (cd "$WT/$dir" && npm ci --no-audit --no-fund >/dev/null 2>&1) || return 1
    echo "$now" > "$stamp"
  fi
}

build() {   # the same steps as deploy/docs-ai/Dockerfile, for a host at /
  local head="$1"
  git -C "$WT" checkout -q --detach "$head" || return 1
  deps packages/agui-chat && deps site && deps frontend || return 1
  say "building the widget"
  # the one-script build first (it empties dist), then every on-demand file next to it
  (cd "$WT/packages/agui-chat" && npx vite build --config vite.iife.config.ts >/dev/null 2>&1 &&
     for c in vite.*.config.ts; do
       [ "$c" = vite.iife.config.ts ] || npx vite build --config "$c" >/dev/null 2>&1 || exit 1
     done) || return 1
  say "building the docs site"
  (cd "$WT/site" && DOCS_SITE="http://localhost:$PORT" DOCS_BASE=/ PUBLIC_ASK_AI_URL=/ai/ask/run PUBLIC_DEMO_URL=/demo/ \
     PUBLIC_DEMO_AGENT_URL=/agent/run PUBLIC_PLAYGROUND_URL=/examples/widget/ npm run build >"$WT/.dev-host-site.log" 2>&1) || return 1
  say "building the demo page"
  (cd "$WT/frontend" && npx vite build --base /demo/ >/dev/null 2>&1) || return 1
}

serve() {
  (cd "$WT/backend" && exec uv run uvicorn docs_ai.host:app --host 127.0.0.1 --port "$PORT") &
  SERVER=$!
}

stop() { [ -n "$SERVER" ] && kill "$SERVER" 2>/dev/null && wait "$SERVER" 2>/dev/null; SERVER=""; }
trap 'stop; exit 0' INT TERM

if [ ! -d "$WT" ]; then
  say "creating the checkout at $WT"
  git -C "$REPO" worktree add -q --detach "$WT" "$REF" || { say "could not create the checkout"; exit 1; }
fi

BUILT=""
while true; do
  HEAD_NOW="$(git -C "$REPO" rev-parse "$REF" 2>/dev/null)"
  if [ -n "$HEAD_NOW" ] && [ "$HEAD_NOW" != "$BUILT" ]; then
    say "building ${HEAD_NOW:0:7}"
    if build "$HEAD_NOW"; then
      stop
      serve
      BUILT="$HEAD_NOW"
      say "serving ${HEAD_NOW:0:7} at http://localhost:$PORT/"
    else
      BUILT="$HEAD_NOW"   # do not rebuild a broken head in a loop: the next commit is tried again
      say "the build of ${HEAD_NOW:0:7} failed; still serving the previous one (site log: $WT/.dev-host-site.log)"
      [ -z "$SERVER" ] && serve
    fi
  fi
  if [ -n "$SERVER" ] && ! kill -0 "$SERVER" 2>/dev/null; then
    say "the server stopped; starting it again"
    serve
  fi
  sleep "$EVERY"
done
