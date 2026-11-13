---
title: 'Configuration'
description: 'Models per provider and every YAML key with its default.'
---

formguide is configured from one YAML file (`load_config("formguide.yaml")`) or in code (`GuideConfig(...)`). Both produce the same `GuideConfig`; `FormGuide(config)` then builds the models and stores. Source: [`config.py`](https://github.com/denvasylenko/dushes/blob/main/backend/formguide/config.py), [`models.py`](https://github.com/denvasylenko/dushes/blob/main/backend/formguide/models.py); a complete working file: [`demo/formguide.yaml`](https://github.com/denvasylenko/dushes/blob/main/backend/demo/formguide.yaml); a starter file: `formguide init`.

```
formguide.yaml ──load_config()──▶ GuideConfig ──FormGuide()──▶ models built per role, stores opened, graph compiled
   (${ENV} expanded,                (plain Python:                   (a missing provider package fails here,
    paths relative to the file)      edit it before use)              with the package name to install)
```

Check a file without calling any model: `formguide check --config formguide.yaml`.

## How the file is read

- **Paths** (`data_dir`, `domain_packs.dir`, `knowledge.dir`, `skills.dir`, `checkpointer.sqlite`, `transcripts.dir`) are relative to the YAML file, not to the working directory.
- **`${VAR}`** anywhere in a string value is replaced by the environment variable (`os.path.expandvars`); an unset variable stays as the literal text. Keep secrets in the environment, not in the file.
- **Import strings** `"package.module:attr"` (tools, providers, factories, model classes) are imported with the Python path of the running process, so your own modules must be importable.
- Every key is optional except a model (see below; with no file at all, `FORMGUIDE_MODEL` works too).

## Models

formguide uses four model roles plus one optional one. Each role takes any LangChain chat model.

| Role | Used for | Needs | Falls back to |
|---|---|---|---|
| `agent` | the conversation: answers, tool calls, cards | tool calling, streaming | — (required) |
| `research` | the document researcher (`ask_documents`) | tool calling | `agent` |
| `compile` | compiling business documents into the domain pack | structured output | `agent` |
| `extract` | reading attachments, prefill from free text | structured output; vision / PDF for scans | `agent` |
| `memory.model` | summarizing older turns of long chats | plain text | `research` |

A cheaper model is fine for `research` and `memory`; `extract` needs a model that accepts images or PDFs if users attach scans.

### Three ways to write a model

| Form | Example | What happens |
|---|---|---|
| string `provider:model` | `"openai:gpt-5"` | `init_chat_model("openai:gpt-5")` |
| dict with `provider` + `model` | `{provider: anthropic, model: claude-haiku-5-5, max_tokens: 16000}` | `init_chat_model(model, model_provider=provider, **rest)`; the other keys are constructor arguments of the provider's class |
| dict with `class` | `{class: "langchain_openai:AzureChatOpenAI", azure_deployment: gpt-5, ...}` | imports the class and calls it with the other keys; use this for any class `init_chat_model` does not know, including your own `BaseChatModel` |

In code, also an instance: `Models(agent=AzureChatOpenAI(...))`.

### One model or one per role

```yaml
model: "openai:gpt-5"              # every role uses it
```

```yaml
models:                            # per role; unset roles fall back as in the table above
  agent: {provider: anthropic, model: claude-haiku-5-5, max_tokens: 16000}
  research: "anthropic:claude-haiku-5-5"
```

`models: "openai:gpt-5"` (a string) is the same as `model:`. If both `model` and `models` are present, `models` wins. With neither, the model comes from `FORMGUIDE_MODEL`, else the built-in Anthropic defaults (Claude Haiku 5.5, the cheapest, for every role).

### Providers

Install the provider's LangChain package (the extras `anthropic` and `openai` cover the first three rows) and set its credentials in the environment.

| Provider | YAML | Package | Credentials |
|---|---|---|---|
| Anthropic | `"anthropic:claude-haiku-5-5"` | `langchain-anthropic` | `ANTHROPIC_API_KEY` |
| OpenAI | `"openai:gpt-5"` | `langchain-openai` | `OPENAI_API_KEY` |
| Azure OpenAI | `{class: "langchain_openai:AzureChatOpenAI", azure_deployment: <name>, api_version: "2025-04-01-preview", azure_endpoint: "${AZURE_OPENAI_ENDPOINT}"}` | `langchain-openai` | `AZURE_OPENAI_API_KEY` (or `api_key: "${...}"`) |
| Google Gemini | `"google_genai:gemini-2.5-pro"` | `langchain-google-genai` | `GOOGLE_API_KEY` |
| AWS Bedrock | `{provider: bedrock_converse, model: <model id>, region_name: eu-central-1}` | `langchain-aws` | the usual AWS credentials |
| Ollama (local) | `{provider: ollama, model: llama3.1, base_url: "http://localhost:11434"}` | `langchain-ollama` | none |
| OpenAI-compatible server (vLLM, LM Studio, a gateway) | `{class: "langchain_openai:ChatOpenAI", model: <name>, base_url: "http://my-gateway/v1", api_key: "${GATEWAY_KEY}"}` | `langchain-openai` | the gateway's key |

Extra keys are passed to the model's constructor unchanged, e.g. `temperature`, `max_tokens`, `timeout`, `max_retries`, or Anthropic's `output_config: {effort: low}`. Only Anthropic, OpenAI and Azure OpenAI are covered by the offline tests (their real request payloads); live runs used Anthropic.

### Mixing providers

```yaml
models:
  agent: {class: "langchain_openai:AzureChatOpenAI", azure_deployment: gpt-5, api_version: "2025-04-01-preview",
          azure_endpoint: "${AZURE_OPENAI_ENDPOINT}"}
  research: "openai:gpt-5-mini"
  extract: {provider: anthropic, model: claude-haiku-5-5, max_tokens: 8000}   # vision for scans
memory: {model: "anthropic:claude-haiku-5-5"}
```

## Every key

| Key | Default | Meaning |
|---|---|---|
| `model` / `models` | see above | the models |
| `data_dir` | `data` | where formguide keeps its own files: learned field dependencies (`deps/`), registered layouts (`layouts/`), documents (`kb/`), attachments (`attachments/`), transcripts (`transcripts/`) unless set elsewhere |
| `components.containers` | `Tabs: tabs, Tab: tab, Accordion: accordion, Section: section, Form: form` | your component library's container tags → role. **Replaces** the default map when given |
| `components.fields` | `Input: text, NumberInput: number, TextArea: text, DatePicker: date, Dropdown: select, RadioGroup: radio, MultiSelect: multiselect, Checkbox: bool, FileUpload: file` | field tags → role (`text`, `number`, `date`, `select`, `radio`, `multiselect`, `bool`, `file`) or a **field spec** (below). **Replaces** the default map when given |
| `domain_packs.dir` | none | a folder of `<form_id>.json` packs (persona, flow hints, glossary, rules, PII fields, `starters`: up to 6 opening messages for an empty chat) |
| `domain_packs.packs` | none | packs inline: `{form_id: {...pack}}` |
| `domain_packs.provider` | none | `"module:function"`; `function(form_id) -> dict or None`, e.g. reading from your database |
| `knowledge.dir` | `<data_dir>/kb` | where uploaded business documents are stored |
| `knowledge.index` | `bm25` | `bm25`, or `{factory: "module:make_store", filter: "module:ns_filter", fetch_factor: 5}`: `make_store()` returns any LangChain `VectorStore`; `ns_filter(namespaces)` returns the store's metadata filter (optional) |
| `knowledge.scopes` | each form sees its own namespace | `{form_id: [namespaces]}`, e.g. a form that also sees shared documents |
| `skills.dir` | none | a folder of skills: `<skill>/SKILL.md` with `name`, `description`, `forms`, `tools` |
| `tools` | none | `["module:tool"]`: LangChain `BaseTool` objects offered for every form |
| `memory.max_history_tokens` | `60000` | compact the model's history above this size |
| `memory.keep_turns` | `4` | recent user turns kept verbatim after compaction |
| `memory.model` | the research model | the summarizer |
| `checkpointer` | in memory | `{sqlite: path}` keeps the model's history across restarts (extra `sqlite`); Postgres / Redis savers in code |
| `transcripts` | files under `<data_dir>/transcripts` | `{dir: path}`, or `memory` |
| `max_tool_rounds` | `10` | model ⇄ tool rounds since the user's last input (a message or a card answer); at the limit the agent stops calling tools and replies in text |
| `learn_dependencies` | `true` | persist observed field dependencies per form |
| `interrupt_mode` | `legacy` | cards as `CUSTOM on_interrupt` (CopilotKit), `structured` (AG-UI 1.0 interrupts), or `both` |
| `actions` | all on | switch agent actions off for this deployment: `{ask_user, request_file, confirm_action, focus_field, review_form, ask_documents, extract_from_attachment}`, each `true`, `false` or `auto`. An action that is off is not offered to the model and its prompt rules are left out. `auto` (the default for `ask_documents`, `request_file`, `extract_from_attachment`): documents only when the form has some, files only when attachments are enabled. The client narrows it further with `forwardedProps.capabilities` ([AG-UI events](../agui-events/#capabilities)) |
| `transcription` | off | dictation on the server (`POST /transcribe`): `true`, or `{provider, model, device, compute_type, language, max_seconds, max_bytes}`. `provider`: `faster_whisper` (default, a local Whisper model, the `transcribe` extra; `model: small`, `compute_type: int8`), `openai` (`model: whisper-1` or `gpt-4o-transcribe`) or `"module:function"` (`fn(data, filename, language) -> text`, sync or async). Defaults: `max_seconds: 120`, `max_bytes: 10000000` |
| `attachments` | on | `false`, or `{enabled, privacy_note}`: `enabled: false` turns off uploads and reading attached files; `privacy_note` is shown on upload requests (`privacy`) |
| `confirm_tools` | none | tool names that always need the user's confirmation: the call is held, the user sees a confirm card, and the tool runs only on yes |
| `tracing` | none | `{callbacks: ["module:factory"], tags: [...], otel?: {exporter, endpoint?, headers?, service_name?, sample_ratio?}}`; `otel` exports formguide's spans over OpenTelemetry (`otlp`, `zipkin`, `azure_monitor`, `console`, `host` or a `module:factory`), see [Speed and tracing](../../backend/observability/#opentelemetry-azure-monitor-zipkin-jaeger-datadog-any-otlp-backend). LangChain callback handlers (Langfuse, Phoenix, your own) and extra tags for every turn. LangSmith needs only `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY` in the environment. See [Speed and tracing](../../backend/observability/) |
| `suggestions` | off | quick replies after answers: `true`, or `{enabled, model, max, timeout}`; `model` defaults to the memory model, `max` 3 (up to 5), `timeout` 4 s. Sent as `CUSTOM suggestions {items, applies?}` (`applies`: validated field changes for chips that fill fields); a failure or timeout sends nothing |

## Field specs: how each component stores its value

A field tag can map to an object instead of a role, so the agent reads your form's values correctly and writes card and prefill values in exactly your format. The full explanation with examples is in [Value formats](../../form/value-formats/).

```yaml
components:
  fields:
    Select:      {role: select, value: id, options_prop: items}         # stores "auto"; choices in props.items
    Lookup:      {role: select, option_keys: {id: code, name: title}}   # stores the option object
    RadioGroup:  {role: radio, value: id}
    MultiSelect: {role: multiselect, value: ids}
    Toggle:      {role: bool, true: "Y", false: "N"}
    Calendar:    {role: date, format: "%d.%m.%Y"}                       # or epoch_ms
    Amount:      {role: number, value: string}
    Phone:       {role: text, codec: "my_app.codecs:PhoneCodec"}         # decode(raw, props) / encode(value, props)
```

| Key | Roles | Values | Default |
|---|---|---|---|
| `role` | — | `text`, `number`, `date`, `select`, `radio`, `multiselect`, `bool`, `file` | required |
| `value` | select, radio / multiselect / number | `option`, `id`, `name` / `options`, `ids`, `names` / `number`, `string` | `option` / `options` / `number` |
| `options_prop` | choices | the props key with the choices | `options` |
| `option_keys` | choices | `{id: <key>, name: <key>}` | detected: `id/name`, `value/label`, `key/label`, `value/text`, `code/name`, `code/title`; strings and `{id: label}` objects too |
| `true`, `false` | bool | the stored values | `true`, `false` |
| `format` | date | `iso`, a `strftime` pattern, `epoch_ms` | `iso` |
| `codec` | all | `"module:Class"` with `decode` and/or `encode` | none |

An unknown role or key fails `load_config` with the tag's name. To check a form and a sample config against these specs: `formguide check --config formguide.yaml --jsx form.jsx --form-config config.json`, or `POST /agent/layouts` with `config`.

## Environment variables

| Variable | Effect |
|---|---|
| `FORMGUIDE_MODEL` | the model when the config sets none (`"openai:gpt-5"`) |
| `FORMGUIDE_CONFIG` | the YAML file `create_app()` / `formguide serve` load when given no path (else `./formguide.yaml`) |
| provider keys | `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `AZURE_OPENAI_API_KEY`, ... as the provider package expects. A missing key is named at start-up (a warning), by `formguide check`, and in the chat's error (`model error: no API key (set ...)`); without this the provider SDK only reports "Connection error" |
| anything else | usable in the YAML as `${NAME}` |

## The same in code

```python
from formguide import FormGuide, GuideConfig, Models, KnowledgeBase, VectorStoreIndex, SkillRegistry, DomainPackRegistry
from langchain_openai import AzureChatOpenAI

guide = FormGuide(GuideConfig(
    models=Models(agent=AzureChatOpenAI(azure_deployment="gpt-5", api_version="2025-04-01-preview"),
                  research="openai:gpt-5-mini"),
    domain_packs=DomainPackRegistry(directory="domain_packs"),
    knowledge=KnowledgeBase("data/kb", index=VectorStoreIndex(my_pgvector),
                            scopes={"loan_application": ["loan_application", "bank_common"]}),
    skills=SkillRegistry.from_dir("skills"),
))
```

Or load the YAML and change what you need: `cfg = load_config("formguide.yaml"); cfg.tools.append(my_tool); FormGuide(cfg)`.
