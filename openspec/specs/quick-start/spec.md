# quick-start Specification

## Purpose
Let a team install or copy formguide and have a working agent endpoint in minutes, configured from one file.

## Requirements

### Requirement: Ready-made app
`formguide.app.create_app(config)` SHALL return a FastAPI app with the agent router mounted under a configurable prefix and CORS configurable, accepting a `GuideConfig`, a path to a YAML file, or nothing (defaults).

#### Scenario: Embedding in an existing service
- **WHEN** a team calls `create_app("formguide.yaml", prefix="/agent")`
- **THEN** the app serves the agent endpoints under `/agent`

### Requirement: Command-line interface
A `formguide` command SHALL provide `init [dir]` (write a starter `formguide.yaml`, a skills folder and a domain-pack example), `check --config` (load the configuration and report models, packs, skills and knowledge scopes without calling a model) and `serve --config --host --port`.

#### Scenario: New project
- **WHEN** a developer runs `formguide init my-agent` and `formguide check --config my-agent/formguide.yaml`
- **THEN** the starter files exist and the check reports a valid configuration

### Requirement: One-line configuration
The configuration SHALL need only a model: `model: "<provider>:<name>"` in YAML (one model for every role), or the `FORMGUIDE_MODEL` environment variable with no file. `create_app()` with no argument SHALL read `$FORMGUIDE_CONFIG`, then `./formguide.yaml`, then defaults.

#### Scenario: Minimal file
- **WHEN** `formguide.yaml` contains only `model: "openai:gpt-5"`
- **THEN** every role uses that model and all other settings take their defaults

### Requirement: Light core with extras
The package SHALL install with core dependencies only (LangGraph, LangChain core, Pydantic, PyYAML, pypdf) and offer extras `anthropic`, `openai`, `server`, `research`, `sqlite` and `all`. Optional packages SHALL be imported only when used.

#### Scenario: Core-only install
- **WHEN** formguide is installed without extras
- **THEN** `import formguide` works and only the features that need an extra report what to install

### Requirement: An unknown configuration key is refused
`load_config` SHALL fail with the key's name, and the closest known key when there is one, for a top-level key or a key of a fixed section that the loader does not read. The accepted keys SHALL be listed in `formguide.config.KEYS`, and the documentation's key table SHALL be tested against it.

#### Scenario: A typo in confirm_tools
- **WHEN** a file has `confrim_tools: [send_form]`
- **THEN** loading fails with "confrim_tools (did you mean confirm_tools?)", and no agent starts with a tool that needed a confirmation left unguarded

### Requirement: The check says what is weak and how to fix it
`formguide check` SHALL, with no model call, list what is weak in the host's description of its site (`--site`), of a form (`--jsx` with `--form-config`) and in the environment (`--public` for a public host). Each finding SHALL say where it is, what follows from it and what to write instead. The command SHALL exit with a non-zero code when a finding is an error.

#### Scenario: A phone field the pack does not mark
- **WHEN** a form has a field named for a phone number that the pack's `pii` does not list
- **THEN** the check prints an error that names the field and says to add it to `pii`, and exits with 1

#### Scenario: Warnings only
- **WHEN** the only findings are a page without keywords and a form without documents
- **THEN** the check prints them with their fixes and exits with 0

