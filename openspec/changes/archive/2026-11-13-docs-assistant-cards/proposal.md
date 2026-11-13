## Why

Ask AI answered with a wall of text: code was retyped by the model (and could drift from the docs), "where is it documented" came back as a plain list, and there was nothing to tap next. The chat felt like the form assistant, not like a guide to the docs.

## What Changes

- The docs assistant becomes a small tool-using agent (default model Claude Haiku 5.5). Its tools put cards in the chat: `show_code` (code blocks quoted verbatim from the docs, as tabs), `show_pages` (page cards), `show_steps` (a numbered how-to), `show_card` (a live card from the gallery), `suggest_next` (two or three follow-up questions as chips), and `search_docs` for a second lookup.
- Cards arrive as `CUSTOM docs_card` events after the answer's text; follow-ups as the standard `CUSTOM suggestions`.
- The site's Ask AI gets a `docs` plugin for `<agui-chat>` that draws these cards in the Apple style, and no longer loads the form plugin.
- Limits per conversation (15 questions), per address per day and per site per day.
- The widget reads fenced code with attributes (```yaml title="x").

## Impact

- `backend/docs_ai/` (agent, corpus code blocks, limits), `backend/tests/test_docs_ai.py`, `site/src/ask/` (the plugin), `site/src/components/AskAI.astro`, `packages/agui-chat/src/dom.ts`, docs and `deploy/docs-ai/fly.toml`.
