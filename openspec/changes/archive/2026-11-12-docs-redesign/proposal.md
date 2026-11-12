# Proposal

## Why

The first docs site moved the old pages over but kept their shape: long pages, few runnable examples, a repository tree where a configuration guide should be, and almost nothing on the backend (models per role, providers, domain packs, documents, skills, stores, deployment). A developer cannot go from "what is this" to "copy, paste, it runs" for either side. Good developer docs (LangChain, OpenSpec) open each page with one line, show a short runnable example per variant, back it with a diagram, and let you ask a question in place.

## What Changes

- **New information architecture**: Get started → Backend → Frontend → Your form → Concepts → Reference → Specifications. Every page opens with a one-line summary, then examples (tabs per provider or client), a diagram where flow matters, details in collapsible blocks, and "Next" cards.
- **Backend guides** (new): install and serve, configuration step by step, models and providers, domain packs, business documents, skills and tools, persistence, prefill, deploy and security, observability.
- **Frontend guides** (reworked): choose a client, the chat widget, React, react-hook-form, CopilotKit, any AG-UI client, cards and answers, themes, frontend tools.
- **Diagrams** with Mermaid in guides (themed for light and dark), the hand-drawn SVGs stay on concept pages.
- **Landing page** reworked after openspec.dev: one-line promise, one-command install with copy, the five-step flow, the live demo, "works with" logos as text.
- **AI-friendly docs**: `llms.txt`, `llms-full.txt`, every page as Markdown at `<page>.md`, and on every page "Copy page", "Open in Claude", "Open in ChatGPT".
- **Ask AI**: a chat on every page (the project's own `<agui-chat>`) backed by a small docs assistant server (`backend/docs_ai/`) that answers only from the docs, with copy-paste code and links to the pages it used. The site shows it when built with `PUBLIC_ASK_AI_URL`; without it the button offers "Open in Claude / ChatGPT".

## Capabilities

### New Capabilities
- `docs-assistant`: the docs assistant server.

### Modified Capabilities
- `docs-site`: structure, page anatomy, AI-friendly outputs, the Ask AI entry point.
- `chat-widget`: fenced code blocks with a copy button in answers (the assistant's answers are mostly code).

## Impact

- `site/`: content rewritten and split, new components (page actions, Ask AI, Mermaid), endpoints for `llms.txt` and `.md` pages.
- `packages/agui-chat`: code blocks in `md()`, the copy strings in all seven languages, a test.
- `backend/docs_ai/` (new), tests; `deploy/docs-ai/` (Dockerfile, fly.toml) for deployment (deploying is a separate step, on the user's go-ahead).
- `.github/workflows/docs.yml`: passes `PUBLIC_ASK_AI_URL` from a repository variable.
