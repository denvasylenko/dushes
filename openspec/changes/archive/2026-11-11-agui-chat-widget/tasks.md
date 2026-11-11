# Tasks

## 1. Backend: richer field changes

- [x] 1.1 `previous` / `previous_display` on card changes (`_t_propose_changes`), and in prefill values as well.
- [x] 1.2 `edited` on field-change resumes: `read_decision` returns the edits, the tool-result text mentions them, and the transcript stores `edited`.

## 2. Backend: new interactions

- [x] 2.1 Generalise `ToolCtx.pending_question` into `pending_interaction` with a kind. All waiting tools refuse when one is pending.
- [x] 2.2 `ask_user` `input`:
  - types and bounds;
  - the default from `field`;
  - validation in `read_answer`.
- [x] 2.3 `request_file` tool, `upload` interrupt and `read_upload`. Answer ids are checked against the thread's attachments, and the result names the files.
- [x] 2.4 `confirm_action` tool, `confirm` interrupt and `read_confirm`.
- [x] 2.5 `confirm_tools` config: hold the listed tool call, confirm, then run it or decline.
- [x] 2.6 `guide.py`:
  - transcript kinds `upload` and `confirm`, and `pending_card` for all kinds;
  - structured reasons `request_file` and `confirm_action`;
  - resume statuses.
- [x] 2.7 `tool_progress` events from the researcher's stream writes, with the parent tool call id.
- [x] 2.8 `suggestions` config (`enabled`, `model`, `max`, `timeout`) and the post-turn call in `guide.run`.
- [x] 2.9 Domain pack `starters`: validation, and `GET /threads/{id}` returns `starters` for an empty thread.
- [x] 2.10 Prompt rules: when to request a file, when to confirm an action, and that `input` is used for dates and numbers.

## 3. Widget package core

- [x] 3.1 `packages/agui-chat` scaffold: TypeScript, Vite library build (ESM + IIFE), Vitest with happy-dom, a size budget check, a README.
- [x] 3.2 Transport: SSE `fetch` POST, building RunAgentInput, Stop via AbortController, `resume-style`, and the `agent` adapter.
- [x] 3.3 Element `<agui-chat>`:
  - shadow root with adopted styles;
  - attributes and `options`, updated live;
  - DOM events;
  - modes `floating`, `inline` and `page`;
  - focus trap and Escape, live region, `::part` names.
- [x] 3.4 Theme tokens with light and dark defaults, `theme` attribute, i18n dictionary and `lang`.
- [x] 3.5 Typewriter and word fade ported from Cheese's chat.js; `typing` modes; reduced motion.
- [x] 3.6 Message model and renderer: user, assistant (minimal markdown), notices, errors, typing dots, retry after an error.
- [x] 3.7 Live tool steps:
  - labels, spinner, tick and error;
  - sub-steps from `tool_progress`;
  - collapsing after the run;
  - `tool-steps` option.
- [x] 3.8 Interrupt renderer registry, the generic fallback card, resume, and restoring a pending interrupt.
- [x] 3.9 Frontend tools: registration, running handlers, continuing the run, and optional rendered elements.
- [x] 3.10 Composer:
  - grow, Enter to send, shake on an empty send;
  - Stop;
  - microphone (Web Speech API);
  - quick-reply chips from starters and `suggestions`.
- [x] 3.11 React wrapper: `AguiChat`, with props bridged to options and events.

## 4. formguide plugin

- [x] 4.1 `beforeRun` state, the `ui_directive` handler (default `data-name` scroll), and tool labels for built-in tools in en, ru, uk, de, fr, it and es.
- [x] 4.2 Field-change card:
  - select, diff, reason, edit (text, number, date, option), jump;
  - accept and reject resumes with `names` and `edited`;
  - Undo through `revertChanges` or `applyChanges`.
- [x] 4.3 Question card: options, multiple, text, `input` pickers, number keys.
- [x] 4.4 Upload card: a drop zone, the `accept` filter, upload progress, ids in the resume.
- [x] 4.5 Confirm card, with the danger style.

## 5. Demo and examples

- [x] 5.1 `frontend/` uses `<agui-chat>` with the formguide plugin; the old `Chat` component is removed. The builds pass.
- [x] 5.2 `examples/widget-html/`: a script-tag page served by the demo server, with a settings panel that toggles every option live.
- [x] 5.3 Barber and loan domain packs get `starters`; `suggestions` is enabled in the demo config.

## 6. Tests

- [x] 6.1 Backend:
  - `previous` and `edited`;
  - `input` validation;
  - `request_file` (ids, unknown ids, skip);
  - `confirm_action` and `confirm_tools` (accept runs the tool, decline does not);
  - `tool_progress` order;
  - suggestions (enabled, disabled, timeout, not after a card);
  - starters;
  - structured reasons.
- [x] 6.2 Widget unit tests:
  - SSE parsing and RunAgentInput;
  - typewriter pacing and word boundaries;
  - renderer registry and resume;
  - frontend tool loop;
  - options toggles;
  - the formguide renderers' resume values.
- [x] 6.3 Live check in the browser: the demo with the widget (a card with an edit and Undo, a question, an upload, a confirm, steps, suggestions), the script-tag example, reduced motion and mobile width.
- [x] 6.4 Run `uv run pytest -q` and the widget tests and builds.

## 7. Docs and specs

- [x] 7.1 New `docs/chat-widget.md`: install (npm, script tag, React), every option and attribute, theming tokens and parts, i18n, plugins, a custom renderer and a frontend tool example.
- [x] 7.2 `docs/ui-components.md`: the new interrupt kinds, `previous`, `edited`, `suggestions`, `tool_progress`.
- [x] 7.3 `docs/configuration.md` (`suggestions`, `confirm_tools`, `starters`), `docs/architecture.md`, `README.md`.
- [x] 7.4 `docs/architecture-pages.html`: a new "Chat widget" page and updates to Build the UI and Integrate. Build the site and republish the artifact.
- [x] 7.5 Run `openspec validate --all --strict` and `python3 scripts/check_english.py`.

## Workflow follow-up

- Archive the change with `/opsx:archive` after it is implemented and verified.
