# Design

## Context

The reference is Cheese's `backend/app/site/chat.js` (740 lines, vanilla JS, an IIFE) and `chat.css`. The parts worth keeping:
- **Typewriter:**
  - a rAF loop with `max(55, backlog * 3)` characters per second;
  - it finishes the current word when the word is shorter than 14 characters;
  - it guards surrogate pairs and closes an unfinished `**`.
- **Word fade:** `fadeWords` wraps each newly shown word in a `span.hfc-w` with a negative `animation-delay` equal to the word's age. A full redraw on every frame then never restarts a fade. Marks older than the 450 ms fade are dropped.
- **Look and motion:**
  - a fixed side panel with `transform: translateX(104%)` → `none` and a scrim;
  - a floating button that slides in;
  - typing dots, a `hfc-rec` box-shadow pulse on the microphone, an `hfc-nudge` shake;
  - `hfc-steps` with tick keyframes and `hfc-in` for cards;
  - the whole set switched off by `prefers-reduced-motion`.

It talks to a custom SSE endpoint, keeps state in localStorage, and builds its DOM with string templates against the page's global CSS.

On the formguide side the demo frontend (`frontend/src/App.tsx`) already implements the AG-UI loop over `@ag-ui/client`: frontend tools via `runTurn`, card and question handling, restore from `GET /threads/{id}`. The backend events are defined in `guide.py`. The rationale for this change is in proposal.md.

## Goals / Non-Goals

**Goals:**
- One element, `<agui-chat>`, usable from a script tag, from any bundler or from React. It has no runtime dependencies, and the IIFE build stays under about 35 KB gzipped.
- The look and motion of Cheese's chat, ported faithfully and made themeable.
- A small public API: attributes, an `options` property, `renderers`, `tools`, `plugins`, and DOM events (`agui:event`, `agui:run-start`, `agui:run-end`, `agui:error`).

**Non-Goals:**
- Markdown beyond what chat.js supports: paragraphs, bold, italics, inline code, links, lists. Code highlighting and tables are out.
- A CopilotKit runtime replacement, server-side rendering, or message editing and branching.
- Publishing to npm in this change. The package is built and usable from the repo (`npm pack`); publishing waits for the GitHub/npm decision.

## Decisions

### Web Component with a shadow root and adopted stylesheets

The CSS is a constructed stylesheet shared by every instance, with tokens as custom properties on `:host`. Tokens include:
- `--agui-accent`, `--agui-on-accent`;
- `--agui-bg`, `--agui-surface`, `--agui-ink`, `--agui-ink-2`, `--agui-line`;
- `--agui-radius`, `--agui-font`, `--agui-panel-width`, `--agui-ease`.

They have light defaults and a `prefers-color-scheme: dark` set; `theme="light|dark|auto"` overrides.

The alternative, light DOM and global CSS like chat.js, was rejected: page styles would leak in both directions, which breaks the "install anywhere" goal.

### Rendering: a tiny keyed renderer, not a framework

Messages are kept in a plain array of items: user, assistant, steps, card, notice, error. Each item renders to a DOM node and is updated in place. Only the streaming assistant node is redrawn per frame, as chat.js does. No framework is used, to keep the size small. Renderers for interrupts receive `(payload, ctx)` and return `{el, done: Promise<resume>}`. They use plain DOM helpers (`h(tag, props, ...children)`) that the package exports, so custom renderers look the same.

### Transport

The default transport is `fetch` POST with SSE parsing (`text/event-stream`, `data:` lines, JSON parsing) and an `AbortController` for Stop. It builds `RunAgentInput` itself: runId, threadId, the last message only (the server keeps history), state, tools, `forwardedProps` and `resume[]` or `command.resume` depending on `resume-style` (default `command`). If `chat.agent` is set to an `AbstractAgent`, the widget subscribes to its events instead.

`@ag-ui/client` is not bundled: it pulls in rxjs and would add about 40 KB. The few AG-UI types the chat needs are declared in `src/types.ts`, so the package has no dependencies at all.

### Typewriter and word fade ported as a module

`typewriter.ts` exports `createTypewriter({onFrame, reducedMotion})` with the same constants (55 chars/s, ×3 backlog, 14-character word completion, 450 ms fade) and `fadeWords(el, marks)`. `typing="plain"` bypasses it, and `typing="off"` renders only when a message ends. These constants become options (`typingSpeed`, `fadeMs`) with chat.js's values as defaults.

### Steps from TOOL_CALL events

A run collects `TOOL_CALL_START/END/RESULT` and `tool_progress` into a "steps" item placed above the answer:
- a spinner while running, a tick when done, an error mark when a result is flagged as an error (`error: true`);
- the step list stays collapsed into "Used 3 tools" after the run.

Labels come from `toolLabels` (plugins merge theirs) and fall back to the tool name humanised. The tick animation reuses `hfc-tick`, driven by real completion, not timers as in chat.js.

### Plugin shape

`plugin = {name, renderers?, tools?, toolLabels?, i18n?, beforeRun?(input), onEvent?(ev, ctx)}`. The formguide plugin:
- sets `input.state = getState()` in `beforeRun`;
- handles `ui_directive` in `onEvent`;
- provides renderers for `set_fields`, `ask`, `upload` and `confirm`.

`fieldCard` options default all on. Without `revertChanges`, Undo calls `applyChanges` with the previous values, so the default works with any backend.

### Backend: new pending kinds

These follow the question-card pattern from the previous change:
- `agent/tools.py` adds `request_file` and `confirm_action`. Both set `ctx.pending_interaction = {kind, ...}`, so `pending_question` generalises to one slot with a kind.
- `confirm` in the graph dispatches by kind, and `agent/interaction.py` gains `read_upload` and `read_confirm`.
- `confirm_tools`: when the model calls a listed tool, the `tools` node does not run it. It stores `{kind: "confirm", tool_call: call}`. After an accepted confirmation, `confirm` runs the held tool and returns its result as the tool result. After a decline it returns the declined text.
- `previous` comes from the overlay in `_t_propose_changes` (`form_value` of the current canonical value) and `display` of it.
- `edited` is read in `read_decision`. The text gains "The user edited before applying: loan_amount → 1200000".

### Backend: tool_progress and suggestions

`guide._run` maps the researcher's existing `{"kind": "tool", ...}` stream writes to `CUSTOM tool_progress`, with the parent id taken from the tool call being run (stored on `ToolCtx`).

Suggestions run in `guide.run` after the graph finishes without an interrupt:
- an `asyncio.wait_for` call to the suggestions model with a short prompt, returning JSON with `items`, validated and trimmed;
- skipped if the turn produced no text or `suggestions.enabled` is false.

Doing this outside the graph keeps it out of the model's history and the checkpoint.

### Demo and examples

`frontend/` keeps its form rendering and replaces `Chat` with `<agui-chat>` plus the formguide plugin. `getState` and `applyChanges` already exist there (`baseState` and `pushToJava`). `examples/widget-html/index.html` is a static page served by the demo server at `/examples/widget/`. It shows the script-tag setup against the barber form, using the mock backend for `applyChanges`.

## Risks / Trade-offs

- [Size creep from the Cheese polish] → a size budget check in the package build (fail above 40 KB gzipped for the IIFE).
- [Shadow DOM blocks host CSS customisation] → tokens plus `::part()` names on the panel, the messages, cards, chips, the composer and buttons.
- [Two chat implementations during migration (React demo chat vs widget)] → the demo switches fully in this change, and the old `Chat` component is deleted.
- [`confirm_tools` holding a tool call changes the tool-call order the model expects] → the held call's result arrives as a normal tool result in the same step after the confirmation, so the model sees a standard call and result pair.
- [Suggestions add latency at the end of every turn] → off by default, a 4 s timeout, a cheap model; sent before `RUN_FINISHED`, while the user is still reading the answer.
- [Speech recognition differs between browsers] → only shown where `SpeechRecognition` exists; no server transcription in this change (chat.js has a server fallback; that is a later option, `micEndpoint`).

## Migration Plan

Additive for API users. The demo's chat UI changes; the old chat code is removed in the same change. Rollback means reverting the change. The backend additions are inert unless the model uses the new tools, or `suggestions` / `confirm_tools` are configured.

## Open Questions

- The npm package name and scope (`@formguide/agui-chat` assumed) depend on the GitHub/npm organisation. Changing it later only touches package.json and docs.
