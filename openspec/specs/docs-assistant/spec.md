# docs-assistant Specification

## Purpose
Answer developers' questions about formguide on the docs site, only from the documentation, with code they can paste and links to the pages used.

## Requirements

### Requirement: Answers from the docs only
The docs assistant SHALL answer a question using passages retrieved from the documentation corpus, include copy-paste code when the question is about usage, and end with links to the pages it used. When the corpus has nothing relevant it SHALL say so and point to the closest page instead of guessing.

#### Scenario: A configuration question
- **WHEN** a reader asks "How do I use Azure OpenAI for the agent and a cheaper model for research?"
- **THEN** the answer contains a YAML `models:` snippet with both roles and a link to the models guide

### Requirement: AG-UI endpoint
The assistant SHALL serve `POST /ask/run` accepting an AG-UI `RunAgentInput` and streaming AG-UI events: `RUN_STARTED`, a tool step for the search, the streamed answer, and exactly one `RUN_FINISHED` or `RUN_ERROR`.

#### Scenario: The site's chat
- **WHEN** `<agui-chat url=".../ask/run">` sends a question
- **THEN** it shows a "Searching the docs" step and then the streamed answer

### Requirement: Abuse limits
The assistant SHALL limit requests per client address, reject questions longer than a configured length with a short error, allow only the configured site origins, and SHALL NOT store conversations.

#### Scenario: Too many questions
- **WHEN** one address sends more questions than the per-minute limit
- **THEN** the endpoint answers 429 and the chat shows a human error with "Try again"

### Requirement: Corpus refresh
The assistant SHALL load the corpus from the published site's `llms-full.txt` or a local file at start-up, and reload it periodically, keeping the previous corpus when a reload fails.

#### Scenario: The site is updated
- **WHEN** the docs are redeployed with a new page
- **THEN** after the next reload the assistant can cite the new page without a restart
