# model-configuration Specification

## Purpose
Run the agent on any model provider and configure the whole system in code or in a YAML file, so it can be installed or copied into a project and then configured.

## Requirements

### Requirement: Models per role, any provider
Models SHALL be configurable per role (agent, research, compile, extract, memory) as a LangChain chat model instance, an `init_chat_model` string (`provider:model`), a `{provider, model, ...}` mapping, or a `{class: "module:Class", ...kwargs}` mapping. Unset roles SHALL fall back to the agent model (memory falls back to research).

#### Scenario: Azure agent, OpenAI researcher
- **WHEN** the YAML sets `agent` to `langchain_openai:AzureChatOpenAI` and `research` to `openai:gpt-5-mini`
- **THEN** the guide uses those classes and `extract` falls back to the agent model

### Requirement: Provider-neutral requests
Built-in tools SHALL be sent in a provider-neutral function format, attachments as LangChain standard content blocks, and structured output SHALL use the provider's native JSON-schema mode (not forced tool calls). Provider-specific options (for example Anthropic prompt caching on the system prompt) SHALL apply only to models that support them.

#### Scenario: Building requests offline
- **WHEN** a request with the tools, an image and a PDF is built for ChatOpenAI, AzureChatOpenAI and ChatAnthropic
- **THEN** each payload contains the tools and the files in that provider's format

### Requirement: Configuration in code or YAML
The system SHALL accept a `GuideConfig` in code or load one from YAML with paths relative to the file and `${ENV}` variables expanded, covering: models, data directory, component map, domain packs, knowledge base (directory, index, scopes), skills, extra tools, tool-round limit, dependency learning and memory.

#### Scenario: Demo YAML
- **WHEN** `demo/formguide.yaml` is loaded
- **THEN** the guide has Anthropic models, the loan form's scope `[loan_application, bank_common]` and the `gift_cards` skill for the barber form

### Requirement: Persistent stores
The configuration SHALL accept a LangGraph checkpointer and a transcript store, in code or in YAML (`checkpointer: {sqlite: path}`, `transcripts: {dir: path}` or `transcripts: memory`). Without configuration, the checkpointer SHALL default to an in-memory saver and the transcript store to files under the data directory (like dependency maps, documents and attachments).

#### Scenario: Demo configuration
- **WHEN** `demo/formguide.yaml` is loaded
- **THEN** the guide uses an SQLite checkpointer and a file transcript store under `data/`
