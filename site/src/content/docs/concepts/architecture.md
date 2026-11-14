---
title: 'Architecture in text'
description: 'The whole system in one page of prose: components, the turn, context, documents, memory.'
---

Dushes is a chat agent that guides end users through large configurable forms: it shows where to click, explains fields, answers from the business's documents, reads documents the user attaches, and fills fields after the user confirms. Behaviour contracts live in [`openspec/specs/`](../../specifications/); this page explains how the parts fit together. The same material with diagrams, plus the rendered specs, is published at https://denvasylenko.github.io/dushes/.

## 1. System overview

```
Form backend (Java)  ── JSX once, config on every event ──▶  Frontend  ── JSX + pack once, config + message ──▶  FormGuide
        ▲                                                       │  ◀── SSE: text, highlights, confirmation cards ───┘
        └──── accepted change, applied like user input ─────────┘
```

- The **form backend** owns the form: it sends a JSX string with only tags and `name` attributes, and rebuilds a flat config (`props` and `state` keyed by name) after every form event.
- The **frontend** renders the JSX from the config and forwards what it received to the agent. It also applies accepted changes by sending them to the form backend, exactly like manual input.
- **FormGuide** (the library in [`backend/formguide`](https://github.com/denvasylenko/dushes/tree/main/backend/formguide)) turns each message plus the fresh config into a compact context, runs the model and its tools, and streams AG-UI events back.

### The wire: AG-UI

A ready-made client is [`<agui-chat>`](../../frontend/chat-widget/) ([`packages/agui-chat`](https://github.com/denvasylenko/dushes/tree/main/packages/agui-chat)): a dependency-free Web Component with a form plugin that renders every card kind and the agent's live steps. The frontend talks to one endpoint, `POST /agent/run`, with an AG-UI `RunAgentInput`; any AG-UI client works, CopilotKit included, with no CopilotKit runtime server. [`agui.py`](https://github.com/denvasylenko/dushes/blob/main/backend/formguide/agui.py) validates the input and every outgoing event against the official `ag-ui-protocol` models; [`server.py`](https://github.com/denvasylenko/dushes/blob/main/backend/formguide/server.py) is the FastAPI router; [`app.py`](https://github.com/denvasylenko/dushes/blob/main/backend/formguide/app.py) wraps it into an app.

| Request field | Meaning |
|---|---|
| `state` | the form: `{config, jsx_hash, form_id, ui?, attachments?}` |
| `messages` | a trailing `user` message is new text; trailing `tool` messages are frontend tool results (history is kept on the server) |
| `tools` | frontend tools the model may call; they never shadow built-in tools |
| `resume` / `forwardedProps.command.resume` | the answer to a card: `{accepted, config}` (AG-UI 1.0 `cancelled` = rejected) |
| `forwardedProps.prefill` | `{data?, text?, attachment_ids?, language?}`: start from data the app already has |

A run streams `RUN_STARTED`, text (`TEXT_MESSAGE_*`), server tool calls with results (`TOOL_CALL_*`, `TOOL_CALL_RESULT`), frontend tool calls without results, `CUSTOM` events (`ui_directive`, `on_interrupt`, `tool_progress` for sub-steps of a running tool, `suggestions` for quick replies when enabled (each may carry validated field changes in `applies`), `agent_context`, `agent_note`, `text_retract` for a lead taken back, `memory_compacted`), and ends with exactly one `RUN_FINISHED` or `RUN_ERROR`. Five kinds of cards stop a turn, one at a time:
- a field-change card (`type: "set_fields"`), answered `{accepted, config, names?, edited?}`. Each change carries `previous` / `previous_display`; `names` keeps a subset of rows, and `edited` holds values the user changed on the card;
- a question from `ask_user` (`type: "ask"`, `{question, options: [{id, label, value?}], multiple, allow_text, input?, field?, applies?, previous?}`), answered `{answer: {ids?, text?}}`. For an editable choice field the options carry form-format values and `applies: true`: the UI fills the field on the tap and resumes with `{answer, config, ui}`, which `confirm` takes like an accepted card (new baseline and version, the field counts as filled); `input` asks for a typed date, time or number;
- a file request from `request_file` (`type: "upload"`), answered `{attachment_ids}`;
- a confirmation from `confirm_action`, or a call held by `confirm_tools` (`type: "confirm"`, with optional `details` and `consequence`), answered `{accepted}`; a confirmed host tool that returns `{receipt}` adds `CUSTOM receipt`;
- a review from `review_form` (`type: "review"`): progress by section and the issues that block sending, computed from the form, plus the model's warnings and validated fixes; answered `{action: continue | submit | fixed}`.

Which of these actions exist in a run is decided in one place, [`agent/actions.py`](https://github.com/denvasylenko/dushes/blob/main/backend/formguide/agent/actions.py): the `actions` config (`true` / `false` / `auto`), the auto rules (documents present, attachments enabled) and the client's `forwardedProps.capabilities`. An action that is off is not bound to the model and its prompt rules are left out. Richer card data (field kinds, option details, long lists, ranges, consents, document confidence) is derived by the server from the form wherever it can, so the tool schemas barely grow. After an answer from the business documents a `CUSTOM sources` event names them. The full list of optional keys is in [AG-UI events](../../reference/agui-events/).

`cancelled` skips any of them. [`agent/interaction.py`](https://github.com/denvasylenko/dushes/blob/main/backend/formguide/agent/interaction.py) reads all the answers for the graph and the transcript alike. A card is delivered according to `interrupt_mode`: `legacy` (default) as `CUSTOM on_interrupt` with a JSON-string value `{type, card_id, changes}` (the ag-ui-langgraph convention CopilotKit reads), `structured` as `RUN_FINISHED.outcome` interrupts (AG-UI 1.0; `reason` `confirm_field_changes`, `ask_user`, `request_file` or `confirm_action`), or `both`. Registered layouts are kept under `data_dir/layouts/`, so a server restart does not break clients holding a `jsx_hash`. Every run ends with `CUSTOM run_stats` (time to first token, total, each model and tool call, tokens and cache hits; [`stats.py`](https://github.com/denvasylenko/dushes/blob/main/backend/formguide/stats.py)), also logged on `formguide.stats`; each turn is a LangChain run "formguide turn" with the thread, run and form in its metadata, so LangSmith or any configured tracer groups it by conversation ([Speed and tracing](../../backend/observability/)). With `tracing.otel`, [`otel.py`](https://github.com/denvasylenko/dushes/blob/main/backend/formguide/otel.py) also exports Dushes' own OpenTelemetry spans (`formguide.turn` with `formguide.model` / `formguide.tool` children and a `formguide.card` event), built from the same hooks as `run_stats`, and continues the caller's trace from `traceparent`. Quick replies ([`suggestions.py`](https://github.com/denvasylenko/dushes/blob/main/backend/formguide/suggestions.py)) are generated after the graph finishes, by a separate call to a cheap model with a timeout, so they never enter the model's history. `GET /threads/{id}?form_id=` returns the pack's `starters` for an empty thread.

The exact payloads the UI receives (the card's `changes`, the `ui_directive`, value formats per field role) and how the form's components must behave are in [Value formats](../../form/overview/), written for people new to the project.

Principles:
- **The config is the source of truth.** Form state is rebuilt from the config on every turn; it is never stored in the agent's memory, synced or summarized.
- **The core knows no domain.** Loans, bookings and calendars differ only in configuration: domain packs, business documents, skills and the component map.
- **Small context.** The model sees a collapsed outline, the open section and the changes: about 1K tokens instead of about 16K for the loan demo's raw config.
- **Append-only history.** The system prompt is frozen per thread; updates arrive in new messages. This keeps prompt caching effective and keeps models that bind reasoning to the exact prefix working.

### Above the form agent: Dushes

[`formguide/site/`](https://github.com/denvasylenko/dushes/tree/main/backend/formguide/site) adds `Dushes`, one chat for a whole site. A router sends each turn either to Dushes (answers from the site map's sections, `navigate`, `open_form`) or to the form agent (`FormGuide.run`, unchanged, one conversation per form: thread `<site thread>-<form id>`). `open_form` keeps a note that becomes the form agent's first message on the form page. See [Dushes](../../backend/dushes/).

## 2. One turn

```
message + config
      │
    sync ──▶ compact ──▶ llm ──(tool calls)──▶ tools ──▶ llm …
                          │                     │
                          │            propose_changes
                          │                     ▼
                          │                  confirm ── interrupt: card ──▶ frontend ──▶ form backend
                          │                     ▲                                 │
                          │                     └──── resume {accepted, config} ──┘
                          │             frontend tool call ──▶ run ends; the client runs it and the
                          │                                    next run brings the result (see sync)
                          ├──(no text)──▶ nudge ──▶ llm
                          └──(done)──▶ answer
```

| Node | What it does | Safeguard |
|---|---|---|
| `sync` | Diffs the config against the previous snapshot, learns dependencies, builds the context, appends the user message | System prompt frozen; knowledge updates delivered as `<updated_instructions>` |
| `compact` | Summarizes older turns when the history is above the threshold | A failed compaction never blocks the turn |
| `llm` | Streams the reply from its second sentence; withholds short internal notes before tool calls and takes back a short lead when the answer comes after the tools | Retries once without earlier reasoning blocks if the provider rejects them |
| `tools` | Built-in tools, skill tools, configured tools; a frontend tool call ends the run | `propose_changes` validates visibility, availability, read-only and options |
| `confirm` | Interrupt with the card (`set_fields`), question (`ask`), upload request, confirmation or review; afterwards gives the model the form's reaction, which rows were kept (`names`), or the answer (an applied answer also sets the config baseline) | An ignored card or question is closed on the next message; one waiting interaction per step |
| `nudge` | Asks the model to answer if it ended the turn silently | At most once per turn |

After a card is accepted, the model receives the diff (for example "+ appeared tab_collateral") and continues dependent steps: service → barber → date → slot.

The turn runs as a background task, apart from the HTTP response that streams it: if the tab closes or reloads mid-answer, the turn still finishes and its result lands in the transcript; `GET /threads/{id}` reports `running` meanwhile, and `POST /stop` ends a turn (see [Persistence](../../backend/persistence/#a-reload-does-not-lose-the-answer)).

## 3. What the model sees

Every request contains:
1. **System prompt**, frozen per thread: persona, working rules, business rules compiled from documents, filling hints, and the form's skills (name and description only).
2. **History**: the conversation memory (after compaction) and recent turns.
3. **Current message**: `<updated_instructions>` if the form's knowledge changed, the `<form_context>` block, the user's text and notes about attachments.

The form context, built deterministically from the layout (structure and order) and the config (labels, flags, values):

```
NOW (user's local time): 2026-11-11 Wednesday 12:25
FORM "Loan application" · config v4 · fields visible 87/221 · required filled 3/55 · errors 0
1 [Tabs main]  req 3/55 ▶
  1.3 [Tab tab_employment] "Employment & income"  req 1/10 ▶
    1.3.2 [Accordion acc_employer] "Employer"  req 0/6 ▶ open [FOCUS]
    1.3.3 [Accordion acc_business] "Sole proprietor" — hidden (usually appears when employment_type = Sole proprietor (seen 3x))
  1.8 [Tab tab_documents] "Documents & consents" ⊘ disabled, 5 required inside (cause unknown; GUESS: …)
FOCUS 1.3.2 [Accordion acc_employer] "Employer" · cursor in field employer_name
1.3.2.2 employer_inn Input* "Company tax ID" = ∅  ℹ 10 digits, usually in the employment contract
CHANGES v3 → v4:
user: loan_type ∅ → "Car loan" (id=auto)
form reacted:
  + appeared tab_collateral "Collateral" (5 required)
  ⊘→✓ became available loan_purpose "Loan purpose"
```

- Addresses (`1.3.2`) encode nesting and on-screen order.
- Hidden and disabled states are inherited from containers; progress counts only fillable fields.
- Dependencies are not declared in the config; they are learned from diffs and shown once reliable.
- PII fields from the domain pack appear as `<filled>`.
- Deeper detail is available through tools: `get_outline`, `get_fields`, `get_field`, `search_fields`, `get_options`.

## 4. Business documents

```
Manager ──▶ DocumentStore (namespaces: loan_application/, bank_common/, barber_booking/)
                 │ all docs in the form's scope            │ sections
                 ▼                                         ▼
           Compile (one model pass) ──▶ Domain Pack     SearchIndex (BM25 | any VectorStore)
                                        rules, notes          ▲ search in scope
                                        → system prompt       │
                                                        Researcher (deep agent, /docs/<ns>/ read-only)
                                                              ▲ question  │ answer + sources
                                                        Form agent: ask_documents
```

- Documents are uploaded into a **namespace** (by default the form id). **Scopes** list the namespaces a form sees, for example the loan form sees its own documents and `bank_common`.
- **Compilation** turns all documents in scope plus the form's field catalog into a summary, rules with sources, filling hints and field notes. They are merged into the domain pack, so typical questions are answered from the prompt without retrieval.
- The **researcher** handles the long tail. It is a `deepagents` agent with its own context, a cheaper model, the documents as a read-only filesystem and ranked search. Only a short cited answer returns to the conversation.
- Why the whole assistant is not a deep agent: a form chat is many short turns where latency and context size matter; the deep-agent harness would add its overhead to every turn. Only document work is delegated.

## 5. User documents

```
📎 file ──▶ AttachmentStore (per thread) ──▶ extraction call (vision + field catalog, structured output)
                                                   │ values + confidence + evidence + editable now?
                                                   ▼
                                     form agent ──▶ card (editable fields) | remember (locked steps)
```

The document itself never enters the main conversation; only the extracted values do. Values for locked steps are marked "disabled now (fill later)" and proposed when the step unlocks.

## 6. Long conversations

The form state is never summarized, because it is rebuilt from the config every turn. What grows is the dialogue, the per-turn context blocks (about 1K tokens each, stale after the next turn) and tool results.

- **Trigger**: history above `max_history_tokens` (default 60 000).
- **Kept**: the last `keep_turns` user turns (default 4), with reasoning blocks removed.
- **Memory** (written by a cheap model and merged with the previous memory): goal; facts the user gave with exact values and status (in the form / not yet, and why); decisions and preferences; rejected proposals; open questions and next step.
- The memory is prepended to the first kept user message; the frozen system prompt is not edited.

### Two histories

The model's history and the conversation the user sees are kept apart:

| | Model history | Display transcript |
|---|---|---|
| Store | LangGraph checkpointer (in memory by default; `sqlite_checkpointer()`, Postgres, Redis) | `TranscriptStore` (files under `data_dir/transcripts` by default, or your own) |
| Contents | context blocks, tool results, reasoning, the conversation memory after compaction | user messages and attached file names, assistant replies, tool activity, cards with status, errors, notices |
| Compaction | rewritten | never touched |
| Used by | the model | the client, to restore the chat (`GET /threads/{id}`) |

`FormGuide.run` records the transcript from the events it streams, so every transport gets it. Cards carry a `card_id` and move `pending → accepted | rejected` on resume, or `pending → dismissed` when the user writes instead. With a persistent checkpointer and transcript store, the user can close the form, come back after a server restart, see the whole chat, and still answer a pending card. Form values themselves are the form backend's responsibility (the demo keeps them in the browser).

Why the system prompt is frozen: some models (Claude Opus 5.5) bind reasoning blocks to the exact conversation prefix, including the system prompt. When documents were recompiled during an open conversation, the rebuilt prompt invalidated earlier reasoning and the provider rejected the request. Freezing the prompt, delivering updates as `<updated_instructions>`, and retrying once without old reasoning blocks fixed it.

## 7. Configuration and extension points

The full reference (model forms per provider, role fallbacks, every YAML key with its default, environment variables) is [`configuration.md`](../../reference/configuration/).

Quick start: `formguide init my-agent` writes a starter `formguide.yaml`, a domain pack and a skill; `formguide check --config …` loads it without calling a model; `formguide serve --config …` runs the endpoints ([`cli.py`](https://github.com/denvasylenko/dushes/blob/main/backend/formguide/cli.py)). The only required setting is `model:` (or `FORMGUIDE_MODEL`). The package's core dependencies are LangGraph, LangChain core, Pydantic, PyYAML and pypdf; providers, the HTTP layer, the researcher and SQLite are extras (`anthropic`, `openai`, `server`, `research`, `sqlite`, `all`), imported only when used.

### Component value formats

[`form/values.py`](https://github.com/denvasylenko/dushes/blob/main/backend/formguide/form/values.py) sits at the two edges of the agent. `Overlay` **decodes** each stored value and option list through the tag's `FieldSpec` into one canonical value per role:
- text: a string;
- number: a number;
- date: an ISO string;
- select / radio: `{id, name}`;
- multiselect: a list of those;
- bool: a boolean.

Everything else (filled, out of the options, diff, learned dependencies, the model's context) sees only canonical values. Decoding is lenient and never raises; an unreadable value is marked ⚠. `propose_changes` and `suggest_prefill` **encode** the canonical value back into the form's format, so a card's `value` goes to the form backend unchanged; `display` is human text. Option keys are detected from common pairs (`id/name`, `value/label`, ...). `register_form(..., config=)` and `formguide check --jsx --form-config` report values or options that cannot be read. Details for UI developers: [Value formats](../../form/value-formats/).

### Prefill

[`prefill.py`](https://github.com/denvasylenko/dushes/blob/main/backend/formguide/prefill.py): `suggest_prefill(state, data, text, attachments)` validates known data against the form the same way `propose_changes` does — keys that are field names directly, everything else through the extraction model — and marks each value `now` (editable) or `later` (inside a locked or hidden step). In a chat (`prefill=` / `forwardedProps.prefill`), these values become the turn's instruction: the agent proposes the `now` values in one card, keeps the `later` ones, and greets the user; the transcript records a notice instead of a user message.

| What | How |
|---|---|
| Models per role (agent, research, compile, extract, memory) | any LangChain `BaseChatModel`; `"provider:model"` strings; `{provider, model, ...}`; `{class: "module:Class", ...}` |
| Component library | `ComponentMap`: JSX tag → role or `FieldSpec` (how the component stores its value: shape of a choice, options key and keys, checkbox values, date format, codec) |
| Domain packs | shipped with the form › provider callable › packs dict › JSON directory › neutral default |
| Search | `BM25Index` or `VectorStoreIndex(vector_store, filter_builder)` |
| Scopes | form id → list of document namespaces |
| Skills | `SKILL.md` folders or `Skill(...)` in code, scoped to forms, optionally with tools |
| Extra tools | any LangChain `BaseTool` |
| History | any LangGraph checkpointer (`sqlite_checkpointer(path)` included) for the model; any `TranscriptStore` for what the user saw |
| Memory | `MemoryConfig(max_history_tokens, keep_turns, model)` |
| Cards | `interrupt_mode`: `legacy` · `structured` · `both` |
| Actions | `actions: {ask_user, request_file, confirm_action, focus_field, review_form, ask_documents, extract_from_attachment}`: `true` · `false` · `auto`; narrowed per run by the client's capabilities |

Model requirements: tool calling (agent, research), structured output (compile, extract), vision or PDF input (extracting from scans).

See `backend/demo/formguide.yaml` for a complete YAML example and `backend/formguide/config.py` for every option.
