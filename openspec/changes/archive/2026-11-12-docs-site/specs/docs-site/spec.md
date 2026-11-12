## ADDED Requirements

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
