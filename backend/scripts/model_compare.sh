#!/usr/bin/env bash
# The model comparison, one command: the same scenario set per agent model (each run in-process, --repeat 3, one
# user and one judge for every row), optionally a second judge on a sample of each run, then the table
# (scripts/runs/models-latest.md and .json). An internal report: nothing under site/ is written unless SITE=1
# (then also site/src/data/benchmarks/models.json).
#   MODELS="anthropic:claude-haiku-5-5 openai:<id>" SECOND_JUDGE=openai:<id> bash backend/scripts/model_compare.sh
# MODELS        the agent models, space-separated (default: the demo's model alone). Ids as the provider lists them.
# SECOND_JUDGE  another judge for the sample (rejudge.py); empty: skipped.
# SET           the names file (default evals/bench_set.txt), REPEAT (3), SAMPLE (30), JUDGE (anthropic:claude-sonnet-5-5).
# Keys come from the macOS keychain through live.sh (LIVE_OPENAI=1 is set here when an openai: model is named).
set -uo pipefail
cd "$(dirname "$0")/.."
MODELS="${MODELS:-anthropic:claude-haiku-5-5}"
JUDGE="${JUDGE:-anthropic:claude-sonnet-5-5}"
SET="${SET:-evals/bench_set.txt}"
REPEAT="${REPEAT:-3}"
SAMPLE="${SAMPLE:-30}"
SECOND_JUDGE="${SECOND_JUDGE:-}"
site=""; [ "${SITE:-}" = "1" ] && site="--site"
case "$MODELS $SECOND_JUDGE" in *openai:*) export LIVE_OPENAI=1 ;; esac
mkdir -p scripts/runs
list="scripts/runs/model-compare-reports.txt"
second="scripts/runs/model-compare-rejudges.txt"
: > "$list"
: > "$second"
cmds=()
for m in $MODELS; do
  # each run's report is the newest evals-*.json right after it; the rejudge reads that run's transcripts at once
  step="uv run python scripts/evals.py --agent-model $(printf '%q' "$m") --model $JUDGE --repeat $REPEAT --names-file $SET"
  step="$step; r=\$(ls -t scripts/runs/evals-2*.json | head -1); echo \"\$r\" >> $list"
  if [ -n "$SECOND_JUDGE" ]; then
    step="$step; uv run python scripts/rejudge.py \"\$r\" --judge $(printf '%q' "$SECOND_JUDGE") --sample $SAMPLE"
    step="$step && echo \"--rejudge \$(ls -t scripts/runs/rejudge-*.json | head -1)\" >> $second"
  fi
  cmds+=("$step")
done
cmds+=("uv run python scripts/model_bench.py \$(tr '\n' ' ' < $list) \$(tr '\n' ' ' < $second) --prices ../site/src/data/prices.json $site --out scripts/runs/models-latest.md && echo 'table: scripts/runs/models-latest.md'")
bash scripts/live.sh "${cmds[@]}"
