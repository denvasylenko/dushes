## ADDED Requirements

### Requirement: Four top-level tabs
The site SHALL be organised into four tabs in the header, Get started, Frontend, Agents and Reference, each with its own sidebar. The header SHALL hold the logo, the tabs, a centred search, Ask AI and GitHub, and SHALL not hold a demo link.

#### Scenario: Looking for the site agent
- **WHEN** a reader opens the Agents tab
- **THEN** the sidebar shows How it works, UI agent (FormGuide), Site agent (Dushes) and Shared, and the researcher is described under the UI agent

### Requirement: Old addresses redirect
Every page address published before the restructure SHALL redirect to the page that now holds its content.

#### Scenario: An old bookmark
- **WHEN** a reader opens `/backend/models/`
- **THEN** they land on `/agents/shared/models/`

### Requirement: Reference generated from code
The Python reference SHALL be generated at build time from the public API's docstrings, one page per public class with its signature, a parameters table (name, type, default, description), what it returns, an example and a link to its guide. The `<agui-chat>` reference SHALL be generated from the widget's manifest: attributes, properties, events, parts and CSS variables.

#### Scenario: A new parameter
- **WHEN** a developer adds a documented parameter to `Dushes.__init__`
- **THEN** the next build shows it in the Dushes reference page without editing the docs

### Requirement: Spotlight search
Search SHALL open from a ⌘K pill as a sheet with results grouped Guides, Reference and Specs, fully usable by keyboard; with no results it SHALL offer "Ask AI" with the typed question.

#### Scenario: No match
- **WHEN** a reader searches for a phrase no page contains
- **THEN** the sheet offers "Ask AI: '<the phrase>'", and choosing it opens Ask AI with that question

## MODIFIED Requirements

### Requirement: Backend and frontend coverage
The site SHALL cover the frontend under the Frontend tab (choosing a client: the widget, React, react-hook-form, CopilotKit, any AG-UI client, plain HTML; connecting a form; cards, blocks, the card gallery, themes, frontend tools, the site agent in the page, the playground) and the agents under the Agents tab (how it works; the UI agent: domain packs, prefill, skills, cards from blocks, user documents; the site agent: site map, navigation, hand-off; shared: install, configuration, models, business documents, persistence, deploy and security, speed and tracing), each fact in one place.

#### Scenario: Configuring the backend
- **WHEN** a reader needs per-role models with a vector store
- **THEN** Agents → Shared → Configuration shows both as steps with YAML and Python examples and a diagram of how the file becomes a running guide
