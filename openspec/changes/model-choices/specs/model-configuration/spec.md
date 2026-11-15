## ADDED Requirements

### Requirement: Named model choices
`models.choices` SHALL map a name to a label and, optionally, a model per role. The first choice SHALL be the default. A role a choice does not name SHALL be that choice's `agent` model when it has one, and the server's own model for the role otherwise.

#### Scenario: A second model for everything
- **WHEN** the configuration has `choices: {haiku: {}, luna: {agent: "openai:gpt-6-luna"}}`
- **THEN** a run on `luna` uses that model for the agent, its helpers and the researcher, and a run on `haiku` uses the server's models

### Requirement: A run names a choice
A run MAY name a configured choice (`forwardedProps.model`, or `model=` in `run`). A name that is not configured, a choice whose provider key the server lacks, and any `model` on a server without choices SHALL be refused, and a request SHALL never carry a model id of its own.

#### Scenario: An unknown name
- **WHEN** a run names `model: "gpt-9"` and the choices are haiku and luna
- **THEN** the run is refused with the two names, and no model is called

### Requirement: A conversation keeps its model
The first run of a thread SHALL record its choice. A later run that names no choice SHALL use the thread's; a run that names another SHALL be refused with HTTP 409 and the thread's choice, so that the client starts a new conversation. Under Dushes the site thread's choice SHALL apply to its form threads.

#### Scenario: The switch is flipped mid-conversation
- **WHEN** a thread started on haiku gets a run that names luna
- **THEN** the run is refused with `code: "model_fixed"` and `choice: "haiku"`

### Requirement: The client is told which model answers
On a server with choices every run SHALL send, right after `RUN_STARTED`, a `CUSTOM model` event with the choice's name, its label and the agent's model id.

#### Scenario: Under an answer
- **WHEN** a run on luna answers
- **THEN** the client has `{choice: "luna", label: "Luna (experimental)", model: "gpt-6-luna"}` before the first word
