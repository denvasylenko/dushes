## ADDED Requirements

### Requirement: Card gallery
The site SHALL have a card gallery page showing every card and variant the chat widget draws as a live specimen: the shipped `<agui-chat>` renderer with the formguide plugin replaying one recorded server event, with no server. Each specimen SHALL show the event the server sends and, once answered, what the card sends back, and SHALL offer Replay.

#### Scenario: Seeing a date question
- **WHEN** a reader scrolls to the date specimen
- **THEN** the real date card is shown with quick picks, and tapping a day shows the answer the widget sends back (`forwardedProps.command.resume`)

## MODIFIED Requirements

### Requirement: Page anatomy
Every guide page SHALL open with a one-line summary, show at least one complete example that can be copied as is, and end with links to the next steps. Where a choice has variants (model provider, client), the variants SHALL be tabs of the same example. Backend pages SHALL show server code only (YAML, Python, HTTP calls) and frontend pages browser code only; each links to the other side instead of repeating it. Backend configuration SHALL be shown both as YAML and as Python, and every backend and widget guide SHALL end with an "Every option" section listing all its keys with defaults.

#### Scenario: Choosing a provider
- **WHEN** a reader opens the models guide
- **THEN** one configuration example is shown with a tab per provider, each with the YAML line and the same model built in Python

#### Scenario: A frontend page
- **WHEN** a reader opens any frontend guide
- **THEN** it shows no server start command and no model key; server options are named with a link to the backend page
