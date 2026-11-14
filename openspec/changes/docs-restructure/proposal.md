## Why

The docs grew page by page: Backend, Frontend, Your form, Built on, Concepts and Reference each mix tutorials, how-tos and facts, the two agents share one Backend section with duplicated text, and the reference is hand-written, so it drifts from the code. Readers cannot tell where to start or where a fact lives. The owner approved a restructure in the LangChain-docs style, with Diátaxis kinds apart (tutorials, guides, explanation, reference).

## What Changes

- **Top-level tabs** in the header: Get started · Frontend · Agents · Reference, with search centred, Ask AI and GitHub. "Live demo" leaves the header and becomes a page.
- **Get started**: Overview (what Dushes is, one diagram of the UI agent and the site agent), Quickstart (backend and widget on one page, tabs Python / HTML / React), Live demo, Benchmarks (numbers from QA Lead's reports), Open standards (today's "Built on" folded into one page).
- **Frontend**: choose a client (widget, React, react-hook-form, CopilotKit, AG-UI, plain HTML); **Connect your form** (today's "Your form": contract, skeleton, state, value formats, components, troubleshooting); cards, blocks, card gallery, themes, frontend tools, Dushes in the page, playground.
- **Agents**: How it works (today's Concepts); **UI agent (FormGuide)** (domain packs, prefill, skills, cards from blocks, user documents, the researcher); **Site agent (Dushes)** (site map, navigation, hand-off to the UI agent, with room for its own capabilities as they ship: proactive tips, user profile, page context, host actions, change history); **Shared** (install, configuration, models, business documents, memory and persistence, deploy and secure, speed and tracing). Each fact lives once.
- **Naming** (Owner's decision): "Dushes" is the product; the docs label the agents **Site agent (Dushes)** and **UI agent (FormGuide)**, after their classes `Dushes` and `FormGuide`, which are not renamed. There are three agents: the site agent, the UI agent and the researcher, described on the UI agent pages.
- **Reference: facts only, generated from code** so it never drifts: one page per public Python class (signature, parameters with type, default and description, returns, an example, a link to the guide) from docstrings; `<agui-chat>` attributes, properties, events, parts and CSS variables from a manifest of the widget; contracts (HTTP API, AG-UI events, card payloads, form types); configuration keys; CLI; Specifications.
- **Redirects**: every old URL answers with a redirect to its new page.
- **Search**: a Spotlight-like sheet (⌘K pill in the header; results grouped Guides / Reference / Specs; keyboard first; with no results, a row "Ask AI: '…'"), built by the docs design-system session.
- **Out of scope**: Ask AI running on the site agent (a later change behind a flag, compared in QA evals before the switch) and a landing "Try it" built on it.

## Impact

- `site/` (content tree moved, `astro.config.mjs` sidebar topics, redirects, header, new components through the design system), new generators under `site/scripts/` (Python reference from docstrings, widget manifest), `packages/agui-chat` (a manifest of the element, owned by the widget designer), `openspec/specs/docs-site/spec.md`.
- `llms.txt`, `llms-full.txt` and `<page>.md` follow the new paths; Ask AI's corpus follows automatically.
- Owners: Docs Lead (content, IA, redirects, generators); docs design-system session (topic switcher, search sheet); widget designer (the element manifest); Owner (docstrings of the core); QA Lead (benchmark reports).
