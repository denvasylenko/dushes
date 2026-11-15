# Proposal

## Why

The owner (through the CPO, 2026-11-15): every Dushes demo on dushes-ai.fly.dev needs a switch between two models, Haiku and Luna, so that a visitor, and the owner himself, can compare how each answers, hard document questions included. Not in Herefront: the platform stays on Haiku.

Today a server has one model per role, fixed when it starts. The cabinet's list for moving its guest assistant onto the package also asks for a model per run (item 8), so this is a package capability, not demo-only code.

## What Changes

- **Named model choices** in the configuration: `models.choices: {haiku: {...}, luna: {...}}`. A choice is the whole Dushes on that model: the agent, its helpers (memory summary, suggestions, card translation) and the researcher, unless the choice names another model for a role.
- **A run names a choice, never a model id**: `forwardedProps.model` in AG-UI, `model=` in `run()`. A name outside the configuration is refused. Without choices configured nothing changes.
- **A conversation keeps the model it started with**. A run that names another choice on an existing thread is refused, and the page starts a new conversation when the person flips the switch.
- **The client is told which model answers**: a `CUSTOM model` event at the start of every run of a server with choices.
- **The demo host** offers the two choices from its configuration, prices each run by its own model, keeps a daily budget per choice and in total (the owner: $3 Haiku + $2 Luna, $5 in all), falls back to the other choice with a line in the chat when one budget is used up, and lists what is usable at `GET /agent/models`.
- **Ask AI** takes the same two choices; its conversation can change model in place.

## Capabilities

- `model-configuration` (modified): choices, the run's choice, the thread's model, the event.
- `docs-assistant` (modified): the docs assistant's choices and the demo host's budgets.

## Impact

- `backend/formguide/` (config, guide, site guide, AG-UI input, server), `backend/docs_ai/` (host, app), `backend/demo/formguide.hosted.yaml`.
- No key reaches a page: the OpenAI key is a Fly secret the owner sets; Luna is listed as usable only when the server has it.
- Outside the core, as requests: the switch and the "answered by" line in the widget and the demo pages (widget designer under Head of Design); the image needs `site/src/data/prices.json` and the secret command (SRE); the docs (Docs Lead); QA's scenarios and a live smoke on both models.
- QA measured Luna at 79% against Haiku's 91% on our scenarios: Haiku stays the default and the switch reads "Luna (experimental)".
