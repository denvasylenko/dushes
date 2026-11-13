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
Every guide page SHALL open with a one-line summary and an at-a-glance block (what it is, when you need it, what you write), show at least one complete example that can be copied as is, and end with links to the next steps. Where a choice has variants (model provider, client), the variants SHALL be tabs of the same example.

#### Scenario: Choosing a provider
- **WHEN** a reader opens the models guide
- **THEN** one configuration example is shown with a tab per provider, each with the YAML line and the same model built in Python

### Requirement: Server code and browser code apart
Backend pages SHALL show server code only (YAML, Python, HTTP calls) and frontend pages browser code only; each links to the other side instead of repeating it. Backend configuration SHALL be shown both as YAML and as Python, one under the other (not as tabs), every snippet SHALL import every name it uses, and every backend and widget guide SHALL end with an "Every option" section listing all its keys with defaults.

#### Scenario: A frontend page
- **WHEN** a reader opens any frontend guide
- **THEN** it shows no server start command and no model key; server options are named with a link to the backend page

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

### Requirement: Card gallery
The site SHALL have a card gallery page showing every card and variant the chat widget draws as a live specimen: the shipped `<agui-chat>` renderer with the formguide plugin replaying one recorded server event, with no server. Each specimen SHALL show the event the server sends and, once answered, what the card sends back, and SHALL offer Replay.

#### Scenario: Seeing a date question
- **WHEN** a reader scrolls to the date specimen
- **THEN** the real date card is shown with quick picks, and tapping a day shows the answer the widget sends back (`forwardedProps.command.resume`)

### Requirement: Navigation on every page
Every page, the landing and the card gallery included, SHALL keep the sidebar (on phones, the menu button), so no page is a dead end. On a computer a toggle before the site title SHALL hide and show the sidebar, and the choice SHALL be kept from page to page.

#### Scenario: Leaving the landing
- **WHEN** a reader on the landing page wants another section
- **THEN** the sidebar is there and a tap opens that page

### Requirement: Typed contract
The site SHALL have a page that types every message between the page and the server (register, the form state, a run, the custom events, every card, every answer, the other endpoints) and explains `jsx`, `jsx_hash`, `form_id`, `config`, `ui`, `thread_id` and `card_id`: what each is, who makes it and when it changes.

#### Scenario: What is jsx_hash
- **WHEN** a reader looks up `jsx_hash`
- **THEN** the contract page says it is the id formguide returns for a registered skeleton, sent with every run, and changing only when the JSX changes

### Requirement: Built on
The site SHALL have a "Built on" section explaining what formguide uses from LangGraph (the agent graph, interrupts, checkpointers), LangChain (models, tools, vector stores, callbacks) and AG-UI (the events), listing the Python and browser packages and where every public name is imported from.

#### Scenario: Where does Models come from
- **WHEN** a reader looks for the import of `Models` or `ChatAnthropic`
- **THEN** the "Built on" overview names the module, and every snippet that uses it imports it

### Requirement: Playgrounds
The themes guide SHALL have an inline theme playground (accent, radii, font, scheme) driving a real `<agui-chat>` with a card and generating the `defineTheme` code; a Playground page SHALL embed the full widget playground (`examples/widget-html`) when the site is built with `PUBLIC_PLAYGROUND_URL`, and otherwise say how to run it.

#### Scenario: Dragging the corner radius
- **WHEN** a reader drags "Cards" in the theme playground
- **THEN** the card in the live chat changes its radius at once and the generated code shows the new `card-radius`

### Requirement: One public host
The docs site, Ask AI and a live demo SHALL be servable from one app (`docs_ai.host`): the site at `/`, the assistant at `/ai`, the demo page at `/demo/` with formguide at `/agent`, and Dushes' demo at `/demo/site.html` with `/site`.

#### Scenario: One address for everything
- **WHEN** a reader opens the public host
- **THEN** the docs are at `/`, Ask AI answers at `/ai/ask/run`, and "Live demo" offers Dushes and the form assistant

### Requirement: Public demo limits
The public demo SHALL use an inexpensive model and limit messages per conversation (default 15), per address per day and per site per day, on `/agent/run` and `/site/run` alike, and SHALL refuse document uploads. Answering a card or the hand-off run SHALL not count as a message.

#### Scenario: The sixteenth demo message
- **WHEN** a visitor sends a sixteenth message in one demo chat
- **THEN** the run is refused with a sentence that says the chat reached its limit, and no model is called

#### Scenario: A manager tries to upload
- **WHEN** a visitor posts a document to `/agent/kb/...` on the public host
- **THEN** the request is refused with 403

### Requirement: The whole configuration on one page
The configuration guide SHALL have one section with every configuration key in one file, each with its default and a comment, as YAML and below it the same `GuideConfig` in Python.

#### Scenario: Looking for one place
- **WHEN** a reader opens the configuration guide
- **THEN** "Every key in one file" shows the complete file, and it parses with `load_config`

### Requirement: Setup prompt for coding agents
The quick start and the landing SHALL offer "Set it up with your AI agent": the reader picks the app (any page, React, react-hook-form, CopilotKit, a whole site), the model provider and where the server runs, and copies one prompt for a coding agent.

#### Scenario: No clipboard
- **WHEN** the browser refuses clipboard access
- **THEN** the prompt opens below the button to copy by hand

### Requirement: The setup prompt follows the docs
The copied prompt SHALL list the exact steps and link the relevant pages as Markdown (`<page>.md`) and `llms.txt`, and SHALL tell the agent to follow them without inventing keys, endpoints or options.

#### Scenario: Azure and react-hook-form
- **WHEN** a reader picks react-hook-form and Azure OpenAI and taps "Copy prompt"
- **THEN** the clipboard holds a prompt with the Azure model block for `formguide.yaml`, `useFormguide` from `@formguide/agui-chat/react-hook-form`, and links to the react-hook-form and models pages as Markdown

### Requirement: One design system for docs UI
Every component on the docs site SHALL be built from the primitives in `site/src/components/ui/`, styled only from the `--fg-*` tokens in `site/src/styles/theme.css` in light and dark. A new pattern SHALL be added to that folder before a component uses it. Ask AI's cards, inside the widget's shadow DOM, SHALL follow the same look through the widget's `--agui-*` tokens.

#### Scenario: A disclosure on any page
- **WHEN** a reader opens "See the prompt" under the setup prompt, or a code disclosure in the card gallery
- **THEN** both use the Disclosure primitive: the same chevron, centred on the summary's text line, turning down when open

#### Scenario: Pressable on a phone
- **WHEN** the site is used on a touch screen
- **THEN** every Button, Chip, segment and Copy button is at least 44 px tall, and hover styles do not stick after a tap

### Requirement: Design system page
The Reference section SHALL have a "Design system" page that shows every primitive live, with its states and a usage snippet, and a switch that previews the page in light and dark.

#### Scenario: A guide at a glance
- **WHEN** a reader opens a guide page that starts with a Summary
- **THEN** it shows What, When you need it and You write as labelled rows in one soft tile, stacked label-above-value on a phone, with an optional link to the example

#### Scenario: Checking a component in both themes
- **WHEN** a reader switches "Preview in" to Light or Dark on the design-system page
- **THEN** the whole site's theme changes and every specimen shows that theme
