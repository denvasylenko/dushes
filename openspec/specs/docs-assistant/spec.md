# docs-assistant Specification

## Purpose
Answer developers' questions about formguide on the docs site, only from the documentation, with code they can paste and links to the pages used.

## Requirements

### Requirement: Answers from the docs only
The docs assistant SHALL answer a question using passages retrieved from the documentation corpus, include copy-paste code when the question is about usage, and end with links to the pages it used. When the corpus has nothing relevant it SHALL say so and point to the closest page instead of guessing.

#### Scenario: A configuration question
- **WHEN** a reader asks "How do I use Azure OpenAI for the agent and a cheaper model for research?"
- **THEN** the answer contains a YAML `models:` snippet with both roles and a link to the models guide

### Requirement: Table of contents
Every question SHALL carry the documentation's table of contents (each guide page's title, address and summary), so a question about where something is documented is answered with links to those pages first.

#### Scenario: Where is it documented
- **WHEN** a reader asks "where can I see all the ways to set a model?"
- **THEN** the model receives the table of contents, and the answer starts with a link to the models guide

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

### Requirement: Answer cards
The docs assistant SHALL answer with short text and cards: code quoted verbatim from the documentation (`show_code`, tabs when there are variants), page cards (`show_pages`), a numbered how-to (`show_steps`) and live gallery cards (`show_card`). Cards SHALL be sent as `CUSTOM docs_card` events after the answer's text.

#### Scenario: A how-to question
- **WHEN** a reader asks how to use Azure OpenAI for the agent
- **THEN** the answer has one or two sentences, a code card whose blocks are exactly the documentation's blocks, and a page card for the models guide

### Requirement: Follow-up questions
Every answer SHALL end with two or three follow-up questions sent as `CUSTOM suggestions`, which the chat shows as chips.

#### Scenario: Tapping a follow-up
- **WHEN** the reader taps a follow-up chip
- **THEN** it is sent as the next question

### Requirement: Conversation limits
The assistant SHALL limit questions per conversation (default 15), per address per minute and per day, and per site per day, and SHALL answer a refused request with a human sentence.

#### Scenario: The sixteenth question
- **WHEN** a conversation sends its sixteenth question
- **THEN** the request is refused with "This chat has reached its limit" and no model is called

### Requirement: One answer, few cards
The server SHALL compose the model's cards into one reader-sized answer: at most one code card, its blocks deduplicated by id and by identical code, from one topic, at most three tabs, with the language or stack the question names first; no page card for a page a shown code block already names as its source, at most two pages; at most three cards in all (code or steps, then a live card, then pages).

#### Scenario: The same block twice
- **WHEN** the model calls show_code three times and two calls carry the same YAML line
- **THEN** the reader sees one code card that shows the line once

#### Scenario: A named stack
- **WHEN** the question asks about Python and the model shows a React block before a Python block
- **THEN** the code card starts with the Python block

### Requirement: Typo-tolerant search
A word of the question that the docs never use SHALL be searched together with the closest word the docs do use.

#### Scenario: A misspelling
- **WHEN** the question is "how to configure my pthon"
- **THEN** passages about Python match

### Requirement: Answer recipes
Answer recipes SHALL be Markdown files (`docs_ai/recipes/`, or `DOCS_AI_RECIPES`) with a name, a title, the words that point to them and instructions. For each question the server SHALL pick at most one recipe by its words, without a model call (ties go to the more specific kind), and add its instructions to the model's for that answer.

#### Scenario: A setup question
- **WHEN** the question is "how do I configure the backend model"
- **THEN** the model's instructions for that answer include the configure-backend recipe

#### Scenario: Nothing matches
- **WHEN** the question is "hello"
- **THEN** no recipe is added


### Requirement: The whole configuration
Asked for the whole configuration (every key, all options, the full file), the assistant SHALL show the configuration guide's one-file section as a code card, the YAML first and the same in Python second, regardless of how the search ranks it.

#### Scenario: Every key
- **WHEN** a reader asks "Show me the whole configuration with every key"
- **THEN** the answer has a code card with the complete `formguide.yaml` and its Python equivalent as tabs
