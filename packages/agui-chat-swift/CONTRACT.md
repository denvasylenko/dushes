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
After ten seconds without an event the server sends a comment line (`: keep-alive`); skip it as any SSE comment,
and treat a stream with no bytes at all for thirty seconds as lost. A healthy run can be silent for longer than
that between events (a tool at work; up to two minutes waiting for the thread's previous turn).

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
- Block `search`: an input with matching options under it; a pick is `values[name] = {id, label}`. `source` names a
  list the app itself serves; static `options` need nothing from the app.
- A block whose `type` holds a hyphen (`city-search`) is a host's own component, registered with the web widget.
  A client that has no component for it skips the block and draws the rest of the card.
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
- Name the card you answer: the interrupt id in a structured `resume`, or `forwardedProps.command = {resume,
  card_id}`. An answer for a card that is no longer the open one changes nothing: the run sends `card_result
  {card_id, status: "not_accepted", reason, code: "card_gone"}` and ends. Read the thread again and show the card
  that is open.

The client never writes the form's config on its own authority: it applies an accepted card through the host's
form, takes the config the form computed, and sends that back.

## The site agent (Dushes)

- `state.page.path` says where the person is; `state.form` is the form on that page, when there is one.
- `CUSTOM site_directive {type: "navigate", path, tab?, section?, form_id?, handoff?}`: the host moves. One per
  run, the last one wins. With `form_id` the host opens that form's page and, unless `handoff: "done"`, starts a
  run with `forwardedProps.handoff: true` so the form's UI agent takes over in the same chat.
- From the next release a page opens only on the person's direct request or a yes to an offer; a question gets
  its answer and an offer (a suggestion "Open <page>").
- One conversation: the site thread shows the UI agents' words too; `GET <site>/threads/{id}` restores it.

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

## Voice mode (experimental), voice contract 1

A voice model listens and speaks; the agent does the work exactly as in chat. The server side is
`backend/formguide/voice.py`; a host mounts its routes (the examples use `<host>/voice`) only when it has voice
codes, so every route answers 404 on a host without the mode: show no trace of it then.

The pass. `POST /voice/unlock {code}` gives `{person, pass}` (403 for a wrong code). The pass lives twelve hours
and travels in the `X-Voice-Pass` header of every other call, never in an address. The client never holds a key
of the voice provider.

A native client: one WebSocket. `GET <host>/voice/stream?thread_id=<the chat's threadId>` with the
`X-Voice-Pass` header.

- client to server: binary frames are microphone audio, raw PCM16 little-endian mono at 24 kHz, sent in real time
  (100 ms pieces are fine); a text frame `{"type": "end"}` ends the conversation.
- server to client: binary frames are the voice's audio in the same format (play them in order; frames arrive all
  the time, silence included, so "speaking" comes from the sound level or the `spoken` events); text frames are
  JSON events.
- first event: `{"type": "started", talk, contract: 1, limits: {seconds, silence_seconds}, audio: {format, rate,
  channels}}`. `contract` is the number of this description; routes, frames and events keep their meaning while
  it stays 1, new events may be added (ignore a type you do not know), and a breaking change gets a new number.
  A refusal is `{"type": "refused", "reason"}` and the socket closes: `pass`, `busy` (another conversation),
  `day`, `person_day` (a budget is used up), `unavailable`.
- then, each with `t_ms`: `hearing {delta}` (the person's words as they speak), `heard {text}` (the request the
  voice hands over: send it as an ordinary user message in the same thread; that run is the normal AG-UI run),
  `heard` may carry `answers: {card_id, type, accepted}`: a plain yes or no while a card waits is the answer to
  that card, so accept or reject the card (its own resume) and do not send the words as a message;
  `interrupted` (the person spoke over a turn in progress: the server has stopped that turn, drop what it was
  showing as in progress; the `heard` that follows is the new request);
  `spoken {delta}` (the transcript of what the voice says), `result {text}` (a piece of the agent's answer was given to the
  voice: one run may send several, the first sentences while the rest is still being written), `quiet {card_id}`, `echo {text}` (the voice's own words came back through the microphone and were
  dropped: remove what `hearing` had started to show), `error {code}`, `ended {reason, cost_usd, seconds}` with
  reason `closed`, `time`, `money`, `silence`, `day` or `lost`.

The browser uses WebRTC instead (`POST /voice/session {sdp, thread_id}` gives `{talk, sdp, contract, limits}`, then
`GET /voice/events?talk=` and `POST /voice/end {talk}`); the events are the same.

Filling without a card. In a thread a voice conversation speaks for, a `set_fields` card may carry
`quiet: true`: every value on it was said by the person (it may replace a value already there) and none is a consent. Apply it
through the host's form at once, as an accepted card (the same resume), draw no card, and keep a line with Undo.
A card without the mark waits as always. A consent is never quiet, and neither is a last name, a company name
or an e-mail: the voice reads it back and asks.

Outside voice mode too (from the commit that adds this line): a field-change card may carry `quiet: true` when the
person answered the card before it with a yes in words (they typed "yes" instead of tapping, which closed that
card, and the agent proposed the same values again). The same mark comes when the person said yes to the
assistant's own question that named these values, and when they left the choice to the assistant ("I don't care,
just select something"). Apply it at once in every mode, as a result line with Undo.
A client that ignores the mark shows the card again, as before.

An open conversation is billed by the second, silence included: end it when the person stops, when the app goes
to the background, and when the screen closes.

A host that already knows who the person is (its own session or token) needs no code and no pass: it gives the
voice module a hook that names the person of each request, and the client simply sends its usual credentials
with the socket. Such a host also keeps the money in its own ledger; the limits and the events are the same.
