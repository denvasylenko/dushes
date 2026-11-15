#!/usr/bin/env bash
# The only way to ship the public host dushes-ai (docs site, Ask AI, the live demo; deploy/docs-ai/).
#   bash scripts/deploy.sh <hash>            check, build, test and deploy that commit
#   bash scripts/deploy.sh <hash> --dry-run  everything, the image build included, except the release
# The commit must be in origin/main (pushed). It is checked out into a fresh worktree in /tmp, so nobody's uncommitted
# work and no file outside git can reach the image; the Docker build context is that worktree. The worktree is removed
# at the end, whatever happens. Secrets (ANTHROPIC_API_KEY, DEMO_PRICES) stay on Fly and are not touched.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
APP="dushes-ai"
HOST="https://dushes-ai.fly.dev"
ref="${1:-}"; mode="${2:-}"
[ -n "$ref" ] || { echo "usage: bash scripts/deploy.sh <hash> [--dry-run]" >&2; exit 2; }
[ -z "$mode" ] || [ "$mode" = "--dry-run" ] || { echo "unknown option: $mode" >&2; exit 2; }

cd "$REPO"
git fetch --quiet origin main
hash="$(git rev-parse --verify --quiet "${ref}^{commit}")" || { echo "refuse: unknown commit $ref" >&2; exit 1; }
git merge-base --is-ancestor "$hash" origin/main || { echo "refuse: $ref is not in origin/main (push it first)" >&2; exit 1; }
short="$(git rev-parse --short "$hash")"

wt="$(mktemp -d /tmp/dushes-deploy-XXXXXX)"
cleanup() { cd "$REPO"; git worktree remove --force "$wt" >/dev/null 2>&1 || rm -rf "$wt"; git worktree prune; }
trap cleanup EXIT
git worktree add --detach --quiet "$wt" "$hash"
cd "$wt"
echo "== $short: $(git log -1 --format=%s | cut -c1-100)"

step() {   # step <name> <command...>: run quietly, show the tail on failure and stop
  local name="$1"; shift
  echo "== $name"
  local out
  if out="$("$@" 2>&1)"; then
    echo "$out" | tail -1
  else
    echo "$out" | tail -30; echo "refuse: $name failed" >&2; exit 1
  fi
}

step "specs" npx --yes @fission-ai/openspec@1.17.0 validate --all --strict --no-interactive
step "English only" python3 scripts/check_english.py
step "lock is current" bash -c "cd backend && uv lock --check"   # pyproject.toml and uv.lock agree, as the image's uv sync --frozen assumes
step "backend tests" bash -c "cd backend && uv run --frozen --quiet pytest -q -p no:cacheprovider"   # the locked dependencies, as in the image
step "site install" bash -c "cd site && npm ci --silent --no-audit --no-fund && cd ../packages/agui-chat && npm ci --silent --no-audit --no-fund"
step "site build" bash -c "cd site && npm run -s build"
step "site links" python3 scripts/check_links.py site/dist
step "site exports" python3 scripts/check_exports.py site/dist
step "site contrast" python3 scripts/check_contrast.py
step "widget reference" python3 scripts/check_ts_reference.py   # every public widget type field has a reference row, as in CI
step "doc examples" bash -c "cd backend && uv run --frozen --quiet python ../scripts/check_examples.py"   # every code example in the docs, as in CI
# the host app starts with the hosted config (load_config refuses an unknown key) and answers its health check;
# a placeholder key: start-up calls no model. Port 8188, our own process only, stopped by PID.
host_boot() {
  if curl -s -o /dev/null -m 2 http://127.0.0.1:8188/; then echo "port 8188 is taken by another process"; return 1; fi
  ( cd backend && export PYTHONUNBUFFERED=1 ANTHROPIC_API_KEY=sk-ant-placeholder DEMO_PRICES=0.1,0.5,0.01,0.125 \
    && exec uv run --frozen --quiet uvicorn docs_ai.host:app --host 127.0.0.1 --port 8188 ) > /tmp/dushes-host-boot.log 2>&1 &
  local pid=$! code=000 i
  for i in $(seq 1 90); do
    code="$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8188/ai/health || true)"
    [ "$code" = 200 ] && break; kill -0 "$pid" 2>/dev/null || break; sleep 1
  done
  kill "$pid" 2>/dev/null || true; wait "$pid" 2>/dev/null || true
  [ "$code" = 200 ] || { tail -20 /tmp/dushes-host-boot.log; return 1; }
  echo "health 200 after ${i}s"
}
step "host starts" host_boot

dirty="$(git status --porcelain)"
[ -z "$dirty" ] || { echo "refuse: the worktree changed during build/tests:"; echo "$dirty"; exit 1; } >&2

if [ "$mode" = "--dry-run" ]; then
  # the image is built exactly as fly deploy builds it (remote builder, same Dockerfile and context), not deployed:
  # catches what the checks above cannot, such as a file the site needs but the image does not copy
  step "image build" fly deploy . --app "$APP" --config deploy/docs-ai/fly.toml --dockerfile deploy/docs-ai/Dockerfile \
    --ignorefile deploy/docs-ai/.dockerignore --remote-only --build-only
  echo "== dry run: $short is ready, not deployed"
  echo "   deploy:   bash scripts/deploy.sh $short"
  exit 0
fi

previous="$(fly releases --app "$APP" --image 2>/dev/null | sed -n 2p | grep -o 'registry.fly.io/[^ ]*' || true)"
echo "== fly deploy $short (rollback: fly deploy --app $APP --image ${previous:-<previous image>})"
fly deploy . --app "$APP" --config deploy/docs-ai/fly.toml --dockerfile deploy/docs-ai/Dockerfile \
  --ignorefile deploy/docs-ai/.dockerignore --remote-only
fly releases --app "$APP" 2>/dev/null | sed -n 2p

echo "== smoke"
fail=0
for path in / /get-started/quickstart/ /ai/health /demo/ /widget/agui-chat.iife.js; do
  code="$(curl -s -o /dev/null -m 60 -w '%{http_code}' "$HOST$path")"
  echo "   $code $path"
  [ "$code" = "200" ] || fail=1
done
[ "$fail" = 0 ] || { echo "smoke failed: check $HOST, rollback: fly deploy --app $APP --image ${previous:-<previous image>}" >&2; exit 1; }
echo "== done: $short"
