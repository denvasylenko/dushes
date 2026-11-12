# docs-site Specification

## Purpose
Give formguide one documentation site that shows the product working in seconds, leads each kind of integrator to their path, and stays in sync with the code and the specs.

## Requirements

### Requirement: One documentation site
The project SHALL have one documentation site, built with Astro Starlight from `site/`, with search, light and dark themes and a sidebar of guides, concepts, reference and specifications. It SHALL be the single source of the visual documentation; no separate HTML page or artifact is maintained.

#### Scenario: Building the site
- **WHEN** a developer runs `npm run build` in `site/`
- **THEN** the specs are rendered, the widget is compiled from `packages/agui-chat/src/`, and a static site is written to `site/dist/`, ready for GitHub Pages

### Requirement: Specifications rendered from OpenSpec
The site SHALL render every `openspec/specs/<capability>/spec.md` as its own page at build time, so a change to a spec appears on the next build without editing the site.

#### Scenario: A new capability
- **WHEN** a folder `openspec/specs/new-thing/` with a `spec.md` is added
- **THEN** the next build has a page for `new-thing` under Specifications

### Requirement: A live demo without a backend
The landing page SHALL show the real `<agui-chat>` widget next to a real form, driven by an in-browser agent that replays recorded AG-UI event streams: answers, steps, a field-change card that fills the form with Undo, a question card, and "show me" directives. It SHALL need no server and no API key.

#### Scenario: Filling from the demo
- **WHEN** a visitor taps the starter that asks the assistant to fill the form, then taps the card's main button
- **THEN** the form fields change, and an Undo on the result line puts the previous values back

### Requirement: Deployment
`.github/workflows/docs.yml` SHALL validate the specs, check that the repository is English only, build the site and deploy it to GitHub Pages on push to `main`; pull requests SHALL build without deploying.

#### Scenario: A pull request touching the docs
- **WHEN** a pull request changes a file under `site/` or `openspec/`
- **THEN** the workflow builds the site and fails on a broken build, without deploying

### Requirement: Page anatomy
Every guide page SHALL open with a one-line summary, show at least one complete example that can be copied as is, and end with links to the next steps. Where a choice has variants (model provider, client), the variants SHALL be tabs of the same example.

#### Scenario: Choosing a provider
- **WHEN** a reader opens the models guide
- **THEN** one configuration example is shown with a tab per provider, each a complete YAML snippet

### Requirement: Backend and frontend coverage
The site SHALL have a Backend section (install and serve, configuration, models and providers, domain packs, business documents, skills and tools, persistence, prefill, deploy and security, observability) and a Frontend section (choosing a client, the chat widget, React, react-hook-form, CopilotKit, any AG-UI client, cards, themes, frontend tools).

#### Scenario: Configuring the backend
- **WHEN** a reader needs per-role models with a vector store
- **THEN** the configuration guide shows both as steps with YAML examples and a diagram of how the file becomes a running guide

### Requirement: AI-friendly outputs
The build SHALL publish `/llms.txt` (an index of pages with their summaries), `/llms-full.txt` (every page as Markdown) and each page as Markdown at its address with `.md`. Every page SHALL offer "Copy page", "Open in Claude" and "Open in ChatGPT".

#### Scenario: Copying a page
- **WHEN** a reader taps "Copy page"
- **THEN** the page's Markdown is on the clipboard and the button says "Copied" briefly

### Requirement: Ask AI entry point
Every page SHALL have an "Ask AI" entry point. When the site is built with `PUBLIC_ASK_AI_URL`, it SHALL open the `<agui-chat>` widget connected to the docs assistant; otherwise it SHALL offer to open the current page in Claude or ChatGPT.

#### Scenario: Built without an assistant
- **WHEN** the site is built without `PUBLIC_ASK_AI_URL` and a reader taps "Ask AI"
- **THEN** the reader is offered "Open in Claude" and "Open in ChatGPT" for the current page, and no request goes to any assistant server
