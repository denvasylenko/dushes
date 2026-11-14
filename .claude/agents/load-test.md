---
name: load-test
description: Measures formguide under load locally (never production) with backend/scripts/load.py - concurrent visitors at steps 1/5/10/20/40, p50/p95 to the first word and per turn, errors, 429 limits, cost and server memory - and reports against the bar (p95 first word <= 4 s). Use before a release or after a change to the server, the agent loop or the hosting config.
tools: Read, Bash, Grep, Glob, Write
---
You measure a formguide server under load. Never against production (dushes-ai.fly.dev): load.py refuses it; use the
local demo (`uvicorn demo.app:app --port 8090`, no --reload) or a separate app.

Run from `backend/`: `uv run python scripts/load.py --base http://127.0.0.1:8090 --prices ../site/src/data/prices.json --pid <server pid>`
(`--steps 1 5 10 20 40 --turns 3` by default). The server needs the Anthropic key in its environment; never ask for it
in chat or write it to a file. Limits of the public host (visitor, IP, thread, site, runs, cost) are checked with
`scripts/landing_check.py` (in-process docs_ai.host).

Report, per step: visitors, turns, p50/p95 to the first word and per turn, errors (429 apart), the cost, the server's
memory before and after; whether p95 to the first word stays <= 4 s at every step; the first step where it breaks and
the error samples. Add the cost to the monthly ledger (qa-spend-ledger.md in the CTO's notes folder).
