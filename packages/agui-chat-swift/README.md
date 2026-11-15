# AGUIChat (Swift)

A native SwiftUI client of the Dushes AG-UI servers (decision D-16): the same assistant as `<agui-chat>`, drawn the
way the Claude app draws a chat on iOS. The contract it follows is `CONTRACT.md`; the reference client is
`packages/agui-chat`.

- `AGUIEvent`, `SSEParser`: the events and the stream, decoded; an unknown `type` or `CUSTOM` name never fails.
- `AGUITransport`: `HTTPTransport` (POST `<agent>/run`, SSE; the host gives the URL and its headers, the package
  keeps no secrets) and `ReplayTransport` (a recorded stream, for previews, tests and a host's stand-in mode).
- `ChatStore`: the log (the person's words, answers, tool steps, cards, the host's own cards), suggestions, errors
  with "Try again"; `text_retract`, `card_result`, `site_directive`, `language` handled as the contract says.
  `capabilities` lists only what the package draws: `ask` and `confirm`.
- `ChatView`: answer as plain text, the person's words in a bubble, a steps line, chips, one input line with the
  microphone. Voice is recorded and transcribed by the host (`onMicrophone`).

Translations live in `Sources/AGUIChat/Resources/Localizable.xcstrings` as `\u` escapes (the repository is
English-only): edit the file as JSON, not in Xcode, which writes the characters out.

Tests: `swift test` (macOS). The recorded turn is `Tests/AGUIChatTests/Fixtures/hours-turn.sse`.

- `restore()` builds the log from `GET <agent>/threads/{id}?format=agui` (messages and the pending card); `stop()`
  ends the turn on the server (`POST <agent>/stop`). A run sends the last 8 messages at most (the UI and site agents
  read only the last user message; the docs assistant reads the last few).
- From the review of f3b7f0f: the stream is split on `\n` only (`LineSplitter`; `bytes.lines` also breaks on U+2028,
  U+2029, U+0085 inside JSON strings); a card is answered only by a run that reached `RUN_FINISHED`, otherwise it is
  open again; «Try again» reads the thread first and does not send a message the server already has; `RUN_ERROR
  busy` is not a failure (wait, read the thread); a message typed during a run is queued; `handoff()` starts the
  hand-off run; a card the client cannot draw says so and can be declined (`{accepted: false}`); a failed step uses
  `TOOL_CALL_RESULT.error` when the server sends it.

Not yet: following a turn that is still running after a relaunch, the other cards (`set_fields`, `upload`,
`review`), quoting.
