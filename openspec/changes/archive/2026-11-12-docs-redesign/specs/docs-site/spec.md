## ADDED Requirements

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
