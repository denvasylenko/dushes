# The AG-UI contract a native client must match (brief for `packages/agui-chat-swift`)

Written by the Dushes Tech Lead, 2026-11-15, for the author of this package (decision D-16). The authoritative
texts are the reference pages and the specs named below; this brief says what to read and what is easy to get
wrong.

## Where the contract is written

- `site/src/content/docs/reference/agui-events.md`: every event the servers send, with payloads.
- `site/src/content/docs/reference/http-api.md`: every route (run, layouts, threads, attachments, stop, models).
- `openspec/specs/agui-protocol`, `agent-turn`, `user-questions`, `field-changes`, `action-confirmations`,
  `chat-history`, `dushes`, `chat-widget`, `chat-widget-formguide`: the behaviour, requirement by requirement.
- The reference client is `packages/agui-chat` (TypeScript). When the text and the widget disagree, ask: one of
  them is a defect.

## One run

`POST <agent>/run` with an AG-UI `RunAgentInput` (`threadId`, `runId`, `messages`, `state`, `tools`, `context`,
`forwardedProps`), answered as a stream of events (SSE, or the binary encoding by `Accept`). Three servers speak
it: the UI agent (`/agent/run`), the site agent (`/site/run`) and the docs assistant (`/ai/ask/run`).

As SSE every event is one `data:` line and an empty line. The server escapes U+2028, U+2029 and U+0085 inside
JSON strings, so no event spans lines; a client should still split the byte stream on `\n` only.

A run is one of: a new user message (the last `messages` item, role user); a card answer (`resume`, or
`forwardedProps.command.resume`); results of client tools (trailing `tool` messages); a prefilled start
(`forwardedProps.prefill`); a hand-off (`forwardedProps.handoff`, site agent to form).

`forwardedProps` the server reads: `capabilities`, `command`, `handoff`, `prefill`, `reply_to`, `traceparent`,
and from the next release `model` (a name from the server's model choices, never a model id).

## Events, in the order a client meets them

- `RUN_STARTED` first, `RUN_FINISHED` or `RUN_ERROR` last. Nothing follows the terminal event.
- Text: `TEXT_MESSAGE_START` / `_CONTENT` (deltas) / `_END`, keyed by `messageId`. One run can hold several
  messages. `CUSTOM text_retract {messageId}` takes a message back: remove it (a lead written before tools, or a
  list of options the card now shows). A shorter message may follow at once.
- Tools: `TOOL_CALL_START` / `_ARGS` / `_END` / `_RESULT`. A failure is a result with an error text and
  `error: true`, never a `RUN_ERROR`; a result without `error` worked. A step may carry a `parent_id` (the
  researcher's steps under `ask_documents`).
- Cards that wait: `CUSTOM on_interrupt` with a JSON string (legacy mode) and/or `RUN_FINISHED.outcome`
  (structured mode); the value has `type` (`ask`, `set_fields`, `confirm`, `upload`, `review`, `blocks`) and a
  `card_id`. The run ends there; the answer is the next run's `resume`.
- Cards that do not wait: `CUSTOM card` (display cards from blocks), `receipt`, `sources`, `suggestions`.
  `suggestions` is `{items: [string], applies?: [changes | null]}`: items are plain strings, never objects;
  `applies` has the same length and order and is there only when a chip fills fields.
- Around the turn: `CUSTOM language {lang}` (card words follow it), `ui_directive` (highlight a field),
  `site_directive` (see below), `hand_back`, `agent_note`, `agent_context`, `memory_compacted`, `tool_progress`,
  `run_stats` (right before the terminal event; under the site agent there can be two).
- New in the next release: `CUSTOM model {choice, label, model}` right after `RUN_STARTED`; `CUSTOM card_result
  {card_id, status: "not_accepted", reason, field?}` (a refused answer: the card must not look answered);
  `CUSTOM site_offer {tool, title}` (the site agent offered to open something); `CUSTOM notice {text, code}`.

A client ignores a `CUSTOM` name it does not know. It must not fail on one.

## Capabilities: say what you can draw

`forwardedProps.capabilities` is the list of cards and variants this client renders: `ask`, `upload`, `confirm`,
`review`, then variants such as `ask.details`, `ask.compare`, `ask.search`, `ask.date`, `ask.slots`, `ask.range`,
`ask.multi`, `ask.address`, `set.consent`, `set.issues`, `set.document`, `sources`, `confirm.receipt`,
`upload.camera`, `feedback`, `rows`, `card.focus`. The server strips or refuses what a client does not list, and
with no list at all it sends everything. A Swift client should send its real list from the first build: it is
how the server keeps a card the client cannot draw from ever arriving.

## Card answers (the `resume` shapes)

- `set_fields`: `{accepted: true, names?: [...], config?, comment?, edits?}` or `{accepted: false}`. A consent
  row (`consent: true`) starts unticked and is applied only when its name is in `names`.
- `ask`: `{answer: {ids?: [...], text?}, config?}`; several fields: `{answers: {name: value}, config}`.
  When the card has `applies: true` the client fills the field itself and sends the form's new `config` with
  the answer: one tap, no second card.
- `confirm`: `{accepted: true | false}`. `upload`: `{attachment_ids: [...]}` after `POST /attachments`.
- `review`: `{action: "continue" | "submit" | "fixed" | closed, ...}`. `blocks`: `{action, label?, values?}`.
- A cancelled card is `{accepted: false}`. A new message while a card waits closes that card.

The client never writes the form's config on its own authority: it applies an accepted card through the host's
form, takes the config the form computed, and sends that back.

## The site agent (Dushes)

- `state.page.path` says where the person is; `state.form` is the form on that page, when there is one.
- `CUSTOM site_directive {type: "navigate", path, tab?, section?, form_id?, handoff?}`: the host moves. One per
  run, the last one wins. With `form_id` the host opens that form's page and, unless `handoff: "done"`, starts a
  run with `forwardedProps.handoff: true` so the form's agent takes over in the same chat.
- From the next release a page opens only on the person's direct request or a yes to an offer; a question gets
  its answer and an offer (a suggestion "Open <page>").
- One conversation: the site thread shows the form agents' words too; `GET <site>/threads/{id}` restores it.

## History and restore

`GET <agent>/threads/{thread_id}` returns the conversation as the person saw it, with each card's status and the
open card, if any. A native client restores from it on launch; it must not rebuild the chat from its own cache.
A turn runs on when the client goes away; `POST <agent>/stop` ends it.

## What a second client usually gets wrong

1. Treating `RUN_ERROR` as the only failure: a tool error and a refused card answer arrive as ordinary events.
2. Showing a card as answered the moment the person taps: wait for the run; `card_result` may refuse it.
3. Dropping `text_retract`: the chat then shows a list and the card with the same options.
4. Sending no `capabilities`, then meeting a card it cannot draw.
5. Reading `run_stats` as exactly one per run.
6. Hard-coding card words: the server sends the language (`language` event) and the cards' own texts.

## What I would ask of the Swift package

- A conformance run: replay the recorded event streams the docs demo uses (`site/src/demo/`) and QA's scenario
  logs through the Swift client and compare what it draws, card by card, with `<agui-chat>`.
- The widget designer checks behaviour; I review the protocol side and anything that needs a server change. A
  gap in the server contract is asked of the Dushes Tech Lead, not worked around in the client.
