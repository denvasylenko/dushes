# chat-widget Specification

## Purpose
Give any web page a ready-made, installable AG-UI chat (a framework-free Web Component with a React wrapper) that streams answers smoothly, shows the agent's steps, renders interrupts through a registry and can be configured and themed from the UI.

## Requirements

### Requirement: Installable as a Web Component
The package SHALL define a custom element `<agui-chat>` that works without a framework. It SHALL ship as an ES module for bundlers and as a single self-registering script for a `<script>` tag, and it SHALL include a React wrapper. It SHALL have no runtime dependencies.

#### Scenario: One script tag
- **WHEN** a plain HTML page includes the script bundle and `<agui-chat url="/agent/run"></agui-chat>`
- **THEN** a working chat appears and talks to that AG-UI endpoint

#### Scenario: React
- **WHEN** a React app renders `<AguiChat url="/agent/run" plugins={[formguide(...)]} />`
- **THEN** the same element is used and its options and events are bridged to props

### Requirement: Works with any AG-UI agent
The widget SHALL send `RunAgentInput` (thread id, run id, messages, state, tools, forwarded props) to a run URL over SSE with its built-in transport, or run any `AbstractAgent` instance given to it. It SHALL keep one thread id per chat, persisted per page unless the host sets one.

#### Scenario: A custom agent instance
- **WHEN** the host sets `chat.agent = new HttpAgent({...})`
- **THEN** runs go through that agent and its events drive the chat

### Requirement: Streaming text with the typewriter
Streamed assistant text SHALL be revealed:
- at an adaptive speed: at least about 55 characters a second, faster when more text is waiting;
- by whole words, never splitting an emoji;
- with markdown bold already applied to text that is still being typed.

Each newly revealed word SHALL fade in from a slight blur, and a redraw SHALL continue a word's fade instead of restarting it.

#### Scenario: A fast stream
- **WHEN** the agent streams a long answer faster than it can be shown
- **THEN** the reveal speeds up so the text never lags far behind, and finishes shortly after the stream ends

### Requirement: Plain and reduced-motion display
With `typing="plain"`, text SHALL appear as it arrives without effects. With `prefers-reduced-motion`, or for restored messages, text SHALL appear whole, and cards and the panel SHALL not animate.

#### Scenario: Reduced motion
- **WHEN** the user's system asks for reduced motion
- **THEN** text, cards and the panel appear without animation

### Requirement: Live tool steps
While a run is active, the widget SHALL show the agent's tool calls as a step list:
- each step has a label from the label map, or the tool name;
- the step in progress shows a spinner, and a finished step a tick;
- a failed step is marked.

Steps SHALL be collapsible, and `tool-steps="off"` SHALL hide them.

#### Scenario: A search step
- **WHEN** the agent calls `search_fields` and it returns
- **THEN** a labelled step appears with a spinner and turns into a tick

### Requirement: Sub-steps
`CUSTOM tool_progress` events SHALL add sub-steps under their parent step. Frontend tool calls SHALL appear as steps only when they have a label.

#### Scenario: Document research
- **WHEN** the agent calls `ask_documents` and the researcher searches twice
- **THEN** the user sees "Searching the business documents" with two sub-steps, each ticked when done

### Requirement: Interrupt renderer registry
The widget SHALL render each interrupt with the renderer registered for its `type`. Interrupts arrive as `CUSTOM on_interrupt` with a JSON value, or as `RUN_FINISHED.outcome.interrupts`. A renderer SHALL return an element and resolve with a resume value; the widget SHALL then resume the same thread with that value. An interrupt with no renderer SHALL show a generic card with the raw payload and Skip. Pending interrupts SHALL be restored after a reload when the host provides a restore URL.

#### Scenario: A custom interrupt type
- **WHEN** the host registers `chat.renderers.set("pick_seat", renderSeatMap)` and the agent sends `{type: "pick_seat", ...}`
- **THEN** the seat map is shown in the chat, and the chosen seat is sent as the resume value

### Requirement: Frontend tools
The host SHALL register frontend tools with a name, a description, a JSON-schema of parameters and a handler. The widget SHALL send them as `tools` with each run, run the handler when the agent calls one, and continue the run with the result as a `tool` message. A handler MAY render an element into the chat.

#### Scenario: A tool that shows a component
- **WHEN** the agent calls a registered `show_map` tool
- **THEN** the handler's map element appears in the chat and its return value goes back to the agent

### Requirement: Composer
The composer SHALL:
- grow with its text up to a limit;
- send on Enter and insert a new line on Shift+Enter;
- clear after sending;
- show a short shake on an empty send.

Typing dots SHALL show while waiting for the first token. A Stop button SHALL abort a run.

#### Scenario: Empty send
- **WHEN** the user presses Enter in an empty composer
- **THEN** nothing is sent and the composer shakes briefly

### Requirement: Microphone
Where the browser supports speech recognition and `mic` is on, a microphone button SHALL dictate into the composer. Dictation SHALL use `micLang` (default: the chat's language). Sending a message SHALL end the dictation at once, and results that arrive after sending SHALL be dropped. With `micAutoSend`, the message SHALL be sent when dictation stops.

#### Scenario: Dictation then send
- **WHEN** the user dictates a sentence and presses Enter
- **THEN** the message is sent, the composer is cleared and the microphone stops

#### Scenario: A late result after sending
- **WHEN** the recognizer delivers its final result after the message was sent
- **THEN** the composer stays empty

#### Scenario: Hands-free
- **WHEN** `micAutoSend` is on and the user stops dictating
- **THEN** the dictated text is sent as a message

### Requirement: Quick-reply chips
The widget SHALL show quick-reply chips: the starters for an empty chat, and the latest `CUSTOM suggestions` event under the last answer. Clicking a chip SHALL send it as a message. The chips SHALL disappear when the user sends a message.

#### Scenario: A suggestion clicked
- **WHEN** the last answer has the suggestions "What comes next?" and "Fill from my passport"
- **THEN** two chips appear under it, and clicking one sends that text

### Requirement: Configurable from the UI
Every feature SHALL be configurable through attributes, an options object, CSS custom properties and an i18n dictionary:
- `mode`: `floating` (a button and a side panel over a scrim), `inline` or `page`;
- `typing`: `words`, `plain` or `off`;
- `tool-steps`;
- `mic`;
- `quick-replies`;
- per-renderer feature flags;
- labels, theme tokens and language.

Unknown options SHALL be ignored with a console warning. Changes to attributes or options SHALL take effect without reloading the page.

#### Scenario: Turning features off
- **WHEN** the host sets `typing="plain" tool-steps="off" mic="off"`
- **THEN** text appears without the typewriter, no step list is shown and there is no microphone button

#### Scenario: Theming
- **WHEN** the host sets `--agui-accent: #0a7` and `--agui-radius: 4px` on the element
- **THEN** buttons, chips and cards use that colour and radius in both light and dark schemes

### Requirement: Accessible and contained
The widget SHALL render inside a shadow root, so its styles neither leak into nor depend on the page. The chat log SHALL be a live region. The floating panel SHALL trap focus while open and close on Escape. Every control SHALL be reachable by keyboard and labelled. Option chips SHALL be selectable with the number keys while a question card has focus.

#### Scenario: Keyboard only
- **WHEN** a user opens the panel with the keyboard, answers a question card with the 2 key and presses Escape
- **THEN** the answer is sent and the panel closes, returning focus to the floating button

### Requirement: Attachments in the composer
When `attach` is on and an uploader exists (the `upload` option, or a plugin's), the composer SHALL show a paperclip button. The chosen files SHALL be uploaded and listed above the composer, where each can be removed. They SHALL go with the next message: plugins can read them during that run. A message with files and no text SHALL be sent with a default text that asks the agent to use the attached document.

#### Scenario: Sending a passport with a message
- **WHEN** the user attaches `passport.pdf` and sends "Fill in my details"
- **THEN** the run carries the attachment, and the user's bubble shows the file name

### Requirement: Attachment limits
`attachAccept`, `attachMultiple` and `attachMaxMb` SHALL limit the file types offered, the number of files and their size. A file over the size limit SHALL not be uploaded, and the composer SHALL say which file was refused.

#### Scenario: A file that is too big
- **WHEN** `attachMaxMb` is 1 and the user picks a 2 MB file
- **THEN** it is not uploaded and the composer names the file and the limit

### Requirement: Running without a new message
The element SHALL offer `run({forwardedProps, notice?})`, which runs the agent without adding a user message, for example to start from prefill data. When `notice` is given it SHALL be shown as a notice line first.

#### Scenario: Prefill from the host app
- **WHEN** the host calls `chat.run({forwardedProps: {prefill: {data}}, notice: "Prefilled from your profile"})`
- **THEN** the notice appears and the agent's answer follows without a user bubble
