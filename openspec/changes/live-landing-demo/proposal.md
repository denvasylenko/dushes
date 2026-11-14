# Proposal

## Why

The landing demo on the docs site replays a recorded run. The owner decided (via the CTO) that it talks to the live agent instead, the hosted loan demo on dushes-ai, with limits that keep the cost bounded, and falls back to the recording when a limit is reached. The host already limits the public demo per conversation, per address and per day (`docs_ai/host.py`, HTTP 429 with a sentence); what is missing is a per-visitor limit, a daily cost cap counted from real token usage, a limit answer the widget can turn into the replay, and a short life for the public chats.

## What Changes

- **Limits** (environment, defaults): `DEMO_PER_VISITOR_DAY=10` messages per visitor (the `X-Demo-Visitor` header, an id the landing keeps in localStorage), the existing `DEMO_PER_IP_DAY` (an address can hold several visitors), `DEMO_RUNS_DAY=300` runs a day in total, `DEMO_COST_DAY=5` US dollars a day, counted from each run's real tokens (`run_stats`) priced by `DEMO_PRICES` (input, output and cache-read per million tokens, set for the hosted model). Card answers and hand-off runs do not count as messages; they do count toward the cost.
- **The limit answer** (agreed with Docs Lead): before the stream, HTTP 429 with `{"detail": "...", "code": "demo_limit", "reason": "visitor | ip | runs | cost | thread", "link": "<quickstart>"}`; the limits are checked before a run, so no stream starts over a limit. The landing (`PUBLIC_DEMO_AGENT_URL=/agent/run`) turns it into the recorded replay with one line, "The live demo is resting for today: here is a recorded run. Run your own in three commands.", and the link; any other error also falls back to the replay.
- **The landing's own form** (`landing_loan`, the 7-field form `site/src/demo/form.ts` draws): the host registers its skeleton at start-up from `backend/demo/landing/landing_loan.jsx`, with its domain pack in the hosted config, so the public page calls no write endpoint and no client can change the pack. The page reads the hash with `GET /agent/layouts/landing_loan` (`{jsx_hash, form_id}`, read-only, pre-registered forms only) and sends `{config, jsx_hash, form_id: "landing_loan", ui}`. Free text reaches the real model, held to the form by the form agent's prompt (an unrelated question gets a short answer and a way back); cards come exactly as from `/agent/run`.
- **Model and tools**: the hosted config already uses Haiku; effort low; no tool with side effects (the demo form has no submitting tool; uploads to the knowledge base stay off).
- **Logs and data**: one counter file per day (runs, messages, tokens, cost), no message text. The public demo's transcripts and checkpoints are deleted after `DEMO_KEEP_HOURS=24`.

## Capabilities

- `http-api`: the public demo's limits and the `demo_limit` event.

## Impact

`docs_ai/host.py` (limits, cost counting, the event, the clean-up), `deploy/docs-ai` (the environment, set with SRE), Docs Lead wires the landing (visitor id, `demo_limit` → replay), QA adds the limit-path scenario.
