---
title: AG-UI events
description: What a run streams, the four kinds of cards, and how to answer each.
---

A run starts with `RUN_STARTED` and ends with exactly one `RUN_FINISHED` or `RUN_ERROR`; nothing follows `RUN_ERROR`.

| Event | When | What a client does |
| --- | --- | --- |
| `TEXT_MESSAGE_START` / `CONTENT` / `END` | the answer, streamed | show it (the widget types it out) |
| `TOOL_CALL_START` / `ARGS` / `END` / `RESULT` | a server tool ran | show a step ("Searching the form") |
| `TOOL_CALL_*` without a result | a frontend tool was called; the run ends | run the tool, send its result as a `tool` message |
| `CUSTOM ui_directive` | "look here": `{type: "focus", target, reveal: [...], hint}` | open the tabs and accordions in `reveal`, scroll to `target`, highlight it |
| `CUSTOM on_interrupt` | a card (legacy mode): a JSON string `{type, card_id, ...}` | render the card, resume with the answer |
| `CUSTOM tool_progress` | a sub-step of a running tool `{parent_id, name, input}` | nest it under the step |
| `CUSTOM sources` | after an answer that used the business documents: `{items: [{title, section?}]}`, once, before `RUN_FINISHED` | show source chips under the answer |
| `CUSTOM receipt` | a confirmed host tool returned `{receipt: {title?, number?, eta?}}`: the same plus `card_id` of the confirmation | turn that confirmation into a receipt |
| `CUSTOM suggestions` | quick replies `{items, applies?}`; each may carry validated field changes | show chips; a chip with `applies` fills fields at once |
| `CUSTOM run_stats` | right before the terminal event: timings, tokens, cache hits | nothing, or a debug line ([Speed and tracing](../../backend/observability/)) |
| `CUSTOM agent_note`, `agent_context`, `memory_compacted` | internal | nothing, or a debug panel |
| `RUN_FINISHED` | the end; in structured mode `outcome.interrupts[]` carries the card | |
| `RUN_ERROR` | the end, with a message | show a human error and "Try again" |

## Cards

One card at a time stops a turn. `interrupt_mode` picks the channel: `legacy` (default; `CUSTOM on_interrupt`, what CopilotKit reads), `structured` (AG-UI 1.0 `RUN_FINISHED.outcome`) or `both`.

| `type` | Structured `reason` | Shows | Answer (`resume`) |
| --- | --- | --- | --- |
| `set_fields` | `confirm_field_changes` | rows `{name, label, value, display, reason, previous, ...}` with a checkbox each | `{accepted: true, config, names?}` after applying; `{accepted: false}` |
| `ask` | `ask_user` | a question with options, single or multiple, typed answers; `applies` + `field` = tapping fills the field | `{answer: {ids}}`, `{answer: {text}}`, or with `applies` `{answer: {ids}, config}`; `{accepted: false}` skips |
| `upload` | `request_file` | a request for a document | `{attachment_ids}` after uploading; `{accepted: false}` |
| `confirm` | `confirm_action` | an irreversible action named on its button; `details: [{label, value}]` and `consequence` say what is sent | `{accepted: true}` / `{accepted: false}` |
| `review` | `review_form` | `mode` `status` or `submit`; `sections: [{name, label, left, total, reveal}]`; `issues: [{severity, field, label, message, kind?, fix?, source?, reveal}]`: form errors first, then (in `submit`) one `kind: "missing"` row per section with empty required fields, then warnings | `{action: "continue", section?}`, `{action: "submit"}`, `{action: "fixed", names, config}` after applying fixes; `{accepted: false}` closes it |

### Optional keys

All of these are optional: a client that ignores them still works.

| Card | Key | Meaning |
| --- | --- | --- |
| `set_fields` | `changes[].kind` | the field's role (`text`, `number`, `date`, `select`, `radio`, `multiselect`, `bool`, `file`): format values by it (no digit groups in a passport number) |
| `set_fields` | `changes[].consent`, `required`, `doc?` | a consent from the domain pack: shown unticked, applied only when ticked |
| `set_fields` | `changes[].issue` | `{severity: "warning", message}`: a valid value a rule or document flags |
| `set_fields` | `source`, `changes[].confidence` | values from a document: `{kind: "document", title, attachment_id, found}`; `confidence` `high` / `medium` / `low` per row |
| `ask` | `options[].description`, `options[].attrs`, `recommended` | a second line, comparable facts (only when 2+ options share the keys), the best fit |
| `ask` | `suggested`, up to 500 `options` | a field's long list (shown with search) and the likely ones first |
| `ask` | `input: {type: number, min, max, step, unit}` | a range from the field: a slider or stepper |
| `ask` | `input: {type: address}` | an address typed with suggestions from the host |
| `ask` | `fields: [{name, label, input?, required}]` | 2-3 short fields in one card; answer `{answers: {name: value}, config}` |
| `ask` | yes / no options on a checkbox field (ids `yes`, `no`, with values) | tapping fills the checkbox |
| `ask` | `applies` on a date / number / time question | a typed answer fills the field: answer `{answer: {text}, config}` |
| `ask` | `sources` | the documents behind compared numbers |
| `upload` | `privacy` | the configured privacy line |

### Capabilities

A client may send `forwardedProps.capabilities`: the cards and variants it renders. A base card is implied by any of its variants (`ask.details` means it renders `ask`).

`ask`, `upload`, `confirm`, `review` and the variants `ask.details`, `ask.compare`, `ask.search`, `ask.date`, `ask.slots`, `ask.range`, `ask.multi`, `ask.address`, `set.consent`, `set.issues`, `set.document`, `sources`, `confirm.receipt`, `upload.camera`, `feedback`.

Without the list, everything the `actions` config allows is on. With it, an action whose card is missing is not offered to the model, and a variant that is missing is left out of the payload.

In legacy mode the answer goes in `forwardedProps.command.resume`; in structured mode as `resume: [{interrupt_id, status, payload}]`. The full payloads, with examples, are in [Build the form UI](../../frontend/cards/).
