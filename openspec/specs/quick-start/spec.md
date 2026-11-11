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
