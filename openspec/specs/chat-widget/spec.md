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
The widget SHALL send `RunAgentInput` (thread id, run id, messages, state, tools, forwarded props) to a run URL over SSE with its built-in transport, or run any `AbstractAgent` instance given to it. It SHALL keep one thread id per chat, persisted per page unless the host sets one. A generated thread id SHALL come from the browser's cryptographic random source (also on plain-http pages), so it cannot be guessed.

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
While a run is active, the widget SHALL show the tool calls as one line of fixed height in the typing dots' place: a spinner and the current step's label (the label map, or the tool name), changed in place. A chevron SHALL open the step list (collapsed by default; a tick per finished step, a mark per failed one, a repeat merged with its count). At the end the line SHALL read "Done in N s" in place; a list the user opened SHALL stay open. `tool-steps="off"` SHALL hide it.

#### Scenario: A search step
- **WHEN** the agent searches the business documents twice and answers after 4 s
- **THEN** one line reads "Searching the documents…" while it works and "Done in 4 s ›" after, and its list has one row "Searching the documents (2)"

### Requirement: Quick answers show no steps line
The steps line SHALL appear only after the first second of a run, so an answer quicker than that shows no line at all; the content SHALL NOT move when the line appears, changes or ends.

#### Scenario: A quick look-up
- **WHEN** the agent calls a tool and answers within half a second
- **THEN** only the answer appears, with no steps line above it

### Requirement: Built-in themes load on demand
The widget SHALL build in `default`; `contrast`, `glass`, `bold` and `messenger` SHALL ship as packs loaded the first time a chat uses one, showing the default look until the pack arrives.

#### Scenario: A page with the glass theme
- **WHEN** a page sets `theme="glass"` with the one-script build
- **THEN** the chat adds `agui-chat.theme-glass.js` from next to `agui-chat.iife.js` and switches to it when it loads

### Requirement: Typing without animation frames
When no animation frame arrives within 300 ms while an answer is typing (a hidden pane, an occluded window, some in-app web views), the widget SHALL put the text in at once and write the rest of the chat without the typewriter.

#### Scenario: A hidden pane
- **WHEN** the page gets no animation frames while a followed answer streams
- **THEN** the full text appears in its bubble instead of an empty one

### Requirement: A footnote under the composer
The `footnote` option SHALL show a line of text under the composer; a hint or an error SHALL take its place while shown, and the line SHALL keep its height, so nothing below or around the composer moves. An upload SHALL write no text there (its tiles show the progress).

#### Scenario: A warning for every message
- **WHEN** the host sets `footnote: "Don't type passwords"`
- **THEN** the line shows under the composer and stays when a file is attached

### Requirement: Attachments shown in the composer
Attached files SHALL show inside the composer box, above the text: an image as a thumbnail, a document as a tile with its name and type, each with a remove button and a spinner while it uploads. A long row SHALL scroll sideways with its edges fading where there is more. Tapping a thumbnail SHALL open the image large in a modal view that a close button, Esc or a tap beside it closes. A sent message SHALL show its images and documents the same way, above its bubble and outside it.

#### Scenario: Pasting a screenshot
- **WHEN** the user pastes a screenshot into the composer
- **THEN** its thumbnail appears in the composer; a tap shows it large

### Requirement: The launcher in every mode
The `launcher` option SHALL set the launcher's look in every popup mode: `round` (an icon), `pill` (an icon and `launcherLabel`), `none` (hidden: the page opens the chat with `chat.open()`), or `auto` (a pill for the panel, a round button for the bubble). `render.launcher` SHALL replace its content in any mode, and its colours SHALL come from the theme's accent.

#### Scenario: Edit with AI
- **WHEN** a page sets `mode: "floating", launcher: "pill", launcherLabel: "Edit with AI"`
- **THEN** the closed chat shows a pill with the spark and "Edit with AI", named so for screen readers

### Requirement: A panel beside the page
With `modal: false`, the floating panel SHALL leave the page beside it usable on screens wider than 760 px: no scrim, a tap on the page SHALL not close it, focus SHALL not be trapped and the panel SHALL not be `aria-modal`. On a phone it SHALL stay a sheet over the page.

#### Scenario: A draft site next to its assistant
- **WHEN** the host sets `modal: false` and the user taps the site beside the open panel
- **THEN** the site gets the tap and the panel stays open

### Requirement: Actions under an answer
Every answer SHALL end with its actions from `messageActions` (default `copy`): `copy` copies the answer's text, `retry` (on the latest answer only) sends the last message again, `speak` reads it aloud, `like` and `dislike` are a pressed pair, and an action of the host's own `{id, label, icon?, hint?}` shows its label and hint as the tooltip. 

#### Scenario: A feedback pair
- **WHEN** the host sets `messageActions: ['copy', 'like', 'dislike']` and the user taps the thumbs-down
- **THEN** it is pressed, the thumbs-up is not, and `agui:message-action` carries `{id: "dislike", pressed: true}`

### Requirement: One turn, one group
An answer's turn (every text part and card of a run, until the next user message) SHALL read as one group: no actions while it streams, then one actions row after its last piece, text or card; `copy` SHALL copy every text part of the turn. Inside a turn pieces SHALL sit about 8 px apart; turns keep their wider gap. A restored conversation SHALL be grouped the same way.

#### Scenario: Text, then a booking card
- **WHEN** the assistant writes a sentence and then shows a question card in the same run
- **THEN** the card sits close under the sentence and one row of Copy and Reply follows the card once the run ends

### Requirement: The host hears every action
Every tap on an action under an answer SHALL fire `agui:message-action` `{id, messageId, text, pressed?}` and call `onMessageAction`, which skips the built-in behaviour by returning true.

#### Scenario: Forking from an answer
- **WHEN** the host adds `{id: "fork", label: "Fork from here"}` and the user taps it
- **THEN** `onMessageAction("fork", {messageId, text})` is called

### Requirement: When the actions show
On a computer the actions under an answer SHALL show on hover or focus, except under the latest answer, where they stay; on a touch screen they SHALL always show, at a 44 px target.

#### Scenario: An older answer
- **WHEN** the pointer rests on an earlier answer
- **THEN** its actions fade in

### Requirement: Pictures open in the viewer
A picture sent with a message or shown in an answer (an `image` block) SHALL open in the image viewer on a tap, as a real image the browser's own menu works on (right-click or a long press: copy, save); the viewer SHALL NOT block that menu.

#### Scenario: Saving a picture from an answer
- **WHEN** the user taps the terrace photo in a card and then right-clicks it in the viewer
- **THEN** the browser's own menu offers to copy or save the image

### Requirement: Unavailable choices are quiet
A chip that cannot be chosen (a closed day, the chips while an action applies) SHALL be disabled and shown in the tertiary ink with no strike-through, as the iOS calendar shows unavailable days.

#### Scenario: A closed day
- **WHEN** the day strip offers Monday, which is closed
- **THEN** the Monday chip is grey and cannot be tapped, and it is not struck through

### Requirement: Back to the latest message
A user who scrolled up SHALL stay where they read while new text arrives, and a round button over the composer SHALL bring them to the latest message; while the assistant works it SHALL show three dots instead of its arrow. Sending a message SHALL bring the view down.

#### Scenario: Reading back while it answers
- **WHEN** the user scrolls up during an answer
- **THEN** the view stays, the button shows the dots, and a tap on it scrolls to the end

### Requirement: The image view's buttons stay with the picture
In the large view of an image, the close button (and the pencil under it) SHALL sit beside the picture's top right corner, or on it where the screen has no room beside it.

#### Scenario: A wide screenshot on a computer
- **WHEN** the user opens a wide screenshot on a 1000 px wide window
- **THEN** the close button sits just right of the picture's top right corner, not in the corner of the screen

### Requirement: Paging the images of a message
The large view of an image sent with a message SHALL page through that message's images only, with a previous and next arrow and "1 of 2" under the picture, the arrow keys and a swipe; it SHALL not wrap around, and an image still in the composer SHALL have no pager.

#### Scenario: Two screenshots in one message
- **WHEN** the user opens the first of two images sent with a message and presses the right arrow key
- **THEN** the second image shows with "2 of 2", and the next arrow is dimmed

### Requirement: Marking up an attached image
An image still in the composer SHALL offer a pencil in its large view. It SHALL load the markup editor on demand (pen, rectangle, text, a colour, a line width, undo, redo, clear, Save, close) and Save SHALL replace the attachment with the marked-up copy, uploaded like any file, in the same place in the row. A sent image SHALL only be viewed.

#### Scenario: Circling a button
- **WHEN** the user opens a pasted screenshot, taps the pencil, circles a button and taps Save
- **THEN** the composer shows the marked-up copy in place of the screenshot

### Requirement: Hero mode
With `mode="hero"` the chat SHALL show only the composer until the first message (no header, no message list, no empty state). The first message SHALL grow it into the chat in place on screens 760 px wide and more (messages above the composer, at most 70% of the viewport high), and open it as a full-screen sheet with a close button on narrower screens. Closing SHALL return to the field and keep the conversation.

#### Scenario: A landing's field
- **WHEN** a visitor types "Bar Centrale, Pescara" into the hero field on a phone and sends it
- **THEN** a full-screen chat opens with the message and the answer, and closing it shows the field again

### Requirement: Hero mode for the page around it
In hero mode a restore with a running turn SHALL open the chat, as SHALL a conversation to come back to on a wide screen. Opening and closing SHALL dispatch `agui:open` and `agui:close`, and `chat.setPlaceholder(text)` SHALL change the composer's hint.

#### Scenario: Back to a running answer
- **WHEN** the page reloads while a turn is still running
- **THEN** the hero chat opens on its own and `agui:open` fires

### Requirement: Host control of shown messages and cards
`chat.removeMessage(id)` SHALL take back an assistant message already shown (and from the history the chat sends), returning whether it was there. `chat.updateCard(id, patch)` SHALL redraw a shown card in place with its payload merged with `patch`, keeping what a waiting card answers to.

#### Scenario: A host takes back a sentence
- **WHEN** the host calls `removeMessage("m1")` after an action followed that text
- **THEN** the message disappears and the next run's history leaves it out

### Requirement: Following a running turn after a reload
A restore MAY return `follow`, a function giving the running turn's events again. The chat SHALL play them as a live run (typing, steps, cards, quick replies), so the answer goes on word by word after a reload; `follow` SHALL take precedence over `running`.

#### Scenario: Back mid-answer
- **WHEN** a host's restore returns the messages so far and `follow`
- **THEN** the rest of the answer types out in the restored chat

### Requirement: Cards come after their text
A card from the agent SHALL appear after the assistant's text above it has finished typing, and quick replies after both. A card restored after a reload, or shown with `showCard`, SHALL appear at once. In a hidden tab the text SHALL be written at once (no typing).

#### Scenario: A question after a sentence
- **WHEN** the agent writes a sentence and then asks a question card
- **THEN** the card appears below the sentence once its last word is typed, never under a half-typed sentence

### Requirement: Frosted glass cards
The `card-blur` token SHALL set a backdrop blur on cards, so a translucent `card-bg` shows a frosted background (the `glass` and `bold` themes use it).

#### Scenario: Glass
- **WHEN** the page sets `theme="glass"`
- **THEN** cards are translucent with a blur over the conversation's gradient

### Requirement: Routine look-ups show no step list
A plugin MAY name tools as `quietSteps`. A turn whose steps are all such tools SHALL show no step list (the typing dots show the wait); the first other step SHALL show the list with every step of the turn.

#### Scenario: Only looking at the form
- **WHEN** the formguide agent calls `get_fields` and answers
- **THEN** no steps line appears above the answer

### Requirement: Sub-steps
`CUSTOM tool_progress` events (a tool's own sub-steps) SHALL NOT add rows: the line and the list name the tool only. Frontend tool calls SHALL appear as steps only when they have a label.

#### Scenario: Document research
- **WHEN** the agent calls `ask_documents` and the researcher searches twice
- **THEN** the user sees "Searching the documents…", with no "Searching" rows under it

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
The widget SHALL show quick-reply chips: the starters for an empty chat, and the latest `CUSTOM suggestions` event in one row pinned right above the composer (it scrolls sideways; the log does not grow under the answer). Clicking a chip SHALL send it as a message. The chips SHALL disappear when the user sends a message, and come back when the user stops that answer.

#### Scenario: A suggestion clicked
- **WHEN** the last answer has the suggestions "What comes next?" and "Fill from my passport"
- **THEN** two chips appear above the composer, and clicking one sends that text

### Requirement: Suggestions from the page
`chat.setSuggestions(items)` SHALL replace the suggestions above the composer without a run (at most five, `[]` clears them); during a run they SHALL show when it ends.

#### Scenario: A booking made by the page
- **WHEN** the page books the table itself and calls `chat.setSuggestions(["Add a note", "Change the time"])`
- **THEN** the old suggestions go and these two show above the composer

### Requirement: Heights ease
A card that shrinks to its answer and a long message that opens or folds SHALL change height over about 200 ms instead of at once, and a queued message's line SHALL fold away; with reduced motion the change SHALL be immediate. While the user has scrolled up, new content SHALL NOT scroll the log, and the jump-to-latest button SHALL show.

#### Scenario: Answering a question card
- **WHEN** the user taps an option on a question card
- **THEN** the card eases to its question and the answer line, and the content under it moves smoothly

### Requirement: Action chips
A suggestion with changes in `applies` SHALL be marked as filling fields. Clicking it SHALL hand the changes to the plugin that applies them (formguide's `applyChanges`), show the result with Undo, and then send the text. When applying fails, the chips SHALL stay and a readable error SHALL show under them.

#### Scenario: A chip that fills a field
- **WHEN** the user clicks "Change term to 48 months", which carries a change of the term
- **THEN** the term is filled at once, a "✓ Filled in · Loan term · Undo" line appears, and the text is sent

### Requirement: Languages load on demand
English SHALL be built into the widget; the other shipped languages (`ru`, `uk`, `de`, `fr`, `it`, `es`) SHALL be packs loaded the first time a chat needs one: a separate chunk in ES module builds, `agui-chat.lang-<lang>.js` next to `agui-chat.iife.js` in the one-script build. Until the pack arrives, or when it cannot be loaded, the chat SHALL show English, and SHALL switch its texts without a reload when it arrives.

#### Scenario: A chat in Russian
- **WHEN** a page with `lang="ru"` loads the one-script build
- **THEN** the widget adds `agui-chat.lang-ru.js` from the folder of `agui-chat.iife.js`, and the composer's placeholder turns Russian when it loads

#### Scenario: No pack for the language
- **WHEN** the chat's language is `pt` and the host registered no pack
- **THEN** the chat stays in English

### Requirement: Language packs of the host's own
`addLanguage(lang, pack)` SHALL register a pack (`{core, formguide, tools}`) for any language; texts missing from it SHALL stay English. Texts from `options.i18n` and plugins SHALL win over a pack.

#### Scenario: Portuguese from the host
- **WHEN** the host calls `addLanguage('pt', {core: {placeholder: 'Escreva ao assistente'}})` and sets `lang: 'pt'`
- **THEN** the placeholder is Portuguese and the Send button still reads Send

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
When `attach` is on and an uploader exists (the `upload` option, or a plugin's), the composer SHALL show a + button (files and photos, as in the Claude app; a menu once a host has more to add). The chosen files SHALL be uploaded and listed above the composer, where each can be removed. They SHALL go with the next message: plugins can read them during that run. A message with files and no text SHALL be sent with a default text that asks the agent to use the attached document.

#### Scenario: Sending a passport with a message
- **WHEN** the user attaches `passport.pdf` and sends "Fill in my details"
- **THEN** the run carries the attachment, and the user's bubble shows the file name

### Requirement: Attachment limits
`attachAccept`, `attachMultiple` and `attachMaxMb` SHALL limit the file types offered, the number of files and their size. Photos larger than `imageMaxPx` (default 2000) on a side, or than 1.5 MB, SHALL be scaled down and saved as JPEG before upload. A file still over the size limit SHALL not be uploaded, and the composer SHALL say which file was refused.

#### Scenario: A big phone photo
- **WHEN** the user attaches a 10 MB photo
- **THEN** a JPEG of at most 2000 px is uploaded instead

#### Scenario: A file that is too big
- **WHEN** `attachMaxMb` is 1 and the user picks a 2 MB file
- **THEN** it is not uploaded and the composer names the file and the limit

### Requirement: Running without a new message
The element SHALL offer `run({forwardedProps, notice?})`, which runs the agent without adding a user message, for example to start from prefill data. When `notice` is given it SHALL be shown as a notice line first.

#### Scenario: Prefill from the host app
- **WHEN** the host calls `chat.run({forwardedProps: {prefill: {data}}, notice: "Prefilled from your profile"})`
- **THEN** the notice appears and the agent's answer follows without a user bubble

### Requirement: Cards closed by a new message
When the user sends a message while a card waits for an answer, the card SHALL be closed: it SHALL keep its question or title, hide its controls, and say it was replaced by the user's message.

#### Scenario: Typing instead of answering
- **WHEN** a question card is pending and the user sends "Actually, let me think"
- **THEN** the card shows only the question and "Replaced by your message"

### Requirement: Readable errors
A failed run SHALL show a sentence for its kind, with "Try again":
- the network is unreachable;
- access is denied (401 or 403);
- too many requests (429);
- the server failed (5xx);
- the model failed (`RUN_ERROR`).

The server's raw message SHALL only be available as a tooltip.

#### Scenario: The server is down
- **WHEN** the run endpoint answers 503
- **THEN** the chat says the assistant could not answer and to try again in a moment, and offers "Try again"

### Requirement: Touch-size targets and quiet focus
On touch screens (`pointer: coarse`), the following SHALL have a tap area of at least 44×44 px:
- icon buttons;
- chips;
- link buttons in cards.

Focus SHALL be shown as a soft ring only for keyboard focus. The widget SHALL not move focus into new cards on touch screens.

#### Scenario: A phone
- **WHEN** the widget runs on a phone
- **THEN** the send, microphone and + buttons are at least 44 px, and a new card does not steal focus

### Requirement: A hint on slow turns
When a run has shown no text for 4 seconds, a quiet "Still working…" line SHALL appear under the typing dots. It SHALL disappear when text or a card arrives.

#### Scenario: A sleeping server
- **WHEN** the first answer takes 6 seconds
- **THEN** "Still working…" is shown from the 4th second until the answer starts

### Requirement: Empty chat
An empty chat SHALL show the title, an intro and the starters. "New chat" SHALL keep the starters of the current form. Without starters, the intro SHALL not mention suggestions.

#### Scenario: New chat
- **WHEN** the user starts a new chat on a form whose pack has starters
- **THEN** the empty chat shows those starters

### Requirement: Themes
A theme SHALL be an object with optional `extends`, `tokens` (for both schemes), `light`, `dark` and `css` (scoped to the widget). `defineTheme(name, theme)` SHALL register it, and the `theme` option or attribute SHALL apply a registered name or an object. An unknown name SHALL fall back to `default` with one console warning.

#### Scenario: A brand theme
- **WHEN** a page calls `defineTheme("acme", {tokens: {accent: "#0a7f6f"}, dark: {accent: "#4fd1c1"}})` and sets `theme="acme"`
- **THEN** buttons use #0a7f6f in the light scheme and #4fd1c1 in the dark one

#### Scenario: Registered later
- **WHEN** the element has `theme="acme"` before `acme` is defined
- **THEN** it uses the default theme, and switches to `acme` as soon as it is defined

### Requirement: Theme layering
Theme values SHALL override the widget's defaults, and CSS on the element from the page SHALL override the theme. Theme token keys MAY omit the `--agui-` prefix. A value containing `;`, `{` or `}`, and an unknown key, SHALL be ignored with a warning.

#### Scenario: Short keys
- **WHEN** a theme has `tokens: {radius: "4px"}`
- **THEN** `--agui-radius` is 4px inside the widget

### Requirement: Scheme
The `scheme` option and attribute SHALL take `auto`, `light` or `dark`. `auto` SHALL follow the system setting, including changes while the page is open. For compatibility, `theme` set to `auto`, `light` or `dark` SHALL act as the scheme. The element SHALL reflect `data-scheme` (`light` or `dark`) and `data-theme` (the theme name, or `custom` for an object), and keep the `dark` class.

#### Scenario: The system turns dark
- **WHEN** the scheme is `auto` and the system switches to dark mode
- **THEN** the widget turns dark without a reload and `data-scheme` becomes `dark`

#### Scenario: Page CSS per scheme
- **WHEN** the page has `agui-chat[data-scheme="dark"] { --agui-accent: #4fd1c1 }`
- **THEN** that accent applies only in the dark scheme

### Requirement: Complete tokens
Every colour, shadow and radius in the widget's CSS SHALL come from a token. Besides the existing ones, the widget SHALL define `--agui-radius-sm`, `--agui-radius-lg`, `--agui-radius-pill`, `--agui-shadow`, `--agui-scrim`, `--agui-on-ok` and `--agui-on-danger`.

#### Scenario: Square corners
- **WHEN** a theme sets `radius`, `radius-sm`, `radius-lg` and `radius-pill` to `0`
- **THEN** cards, buttons, chips, the composer and the floating button have square corners

### Requirement: Code blocks in answers
The widget SHALL render fenced code blocks (```` ```lang ````) in assistant messages as a monospace block that keeps line breaks and indentation, shows the language, and has a copy button labelled in the chat's language. Tapping it SHALL put the block's text on the clipboard and say "Copied" briefly. A fence still open while the answer streams SHALL already show as code.

#### Scenario: Copying a snippet
- **WHEN** an answer contains a ```` ```yaml ```` block and the user taps its copy button
- **THEN** the clipboard holds exactly the YAML, and the button reads "Copied" for a moment

### Requirement: A part on every element
Every element the widget draws SHALL carry a `part` from a documented vocabulary, including card content (questions, rows, options, calendar days, steppers, review rows, receipts) and the chrome (header, empty chat, messages, steps, suggestions, composer). Parts SHALL be added to elements that appear later, such as a card's result line.

#### Scenario: Styling an option from the page
- **WHEN** the page has `agui-chat::part(option) { border-radius: 0 }` and a question with descriptions arrives
- **THEN** its options have square corners

### Requirement: Component tokens
Cards, bubbles, chips, buttons, inputs, the header, the composer and the calendar SHALL read component tokens (for example `--agui-card-bg`, `--agui-bubble-user-bg`, `--agui-chip-radius`, `--agui-button-bg`) that fall back to the global tokens. Themes SHALL accept them as short keys.

#### Scenario: Only the cards
- **WHEN** a theme sets `card-bg` and nothing else
- **THEN** cards change background and the panel keeps its own

### Requirement: Replaceable icons
The `icons` option SHALL replace any built-in icon (send, stop, mic, clip, plus, close, logo) with an SVG string or an element.

#### Scenario: A brand logo
- **WHEN** `icons: {logo: '<svg ...>'}` is set
- **THEN** the header and the floating button show that logo

### Requirement: Slots for the host's own components
The `render` option SHALL let the host replace pieces with its own elements: `markdown` (the answer's HTML, also while streaming), `assistant`, `user`, `empty`, `header`, `error`, `suggestions`, `sources` and `composer`. A slot that returns nothing, or throws, SHALL fall back to the default, with one console warning for a throw.

#### Scenario: A custom answer component
- **WHEN** `render.assistant` returns an element for a finished answer
- **THEN** that element replaces the bubble's content, and the default is used for answers it returns nothing for

### Requirement: Bubble mode
`mode: "bubble"` SHALL show a round launcher in a corner (`bubbleSide`, default right). Opening SHALL grow the chat window out of the launcher with a spring (or a fade with `motion: "none"` or reduced motion), and the launcher's icon SHALL turn into a close mark. On a computer the page SHALL stay usable; under 520 px the window SHALL be a bottom sheet with a dimmed page.

#### Scenario: Open and close
- **WHEN** the user taps the launcher, then taps it again
- **THEN** the window opens next to the launcher, then shrinks back into it, and focus returns to the launcher

### Requirement: Greeting and unread mark
With `greeting`, a small speech bubble SHALL appear next to the closed launcher after `greetingDelay` seconds (default 4), open the chat when tapped, and not come back once closed. An answer arriving while the bubble is closed SHALL put a dot on the launcher until it is opened.

#### Scenario: An answer while closed
- **WHEN** the bubble is closed and an answer arrives
- **THEN** the launcher shows the unread dot, and opening the chat clears it

### Requirement: Launcher slot
`render.launcher` SHALL replace the launcher's content with the host's element; the widget SHALL keep the click, the open state and the unread dot.

#### Scenario: A custom launcher
- **WHEN** `render.launcher` returns an avatar image
- **THEN** the launcher shows the avatar and still opens the chat

### Requirement: Calling a card from code
`chat.showCard(payload)` SHALL render any card type the chat has a renderer for, without the agent, and SHALL return a promise that resolves with the user's answer (the same value a resume would carry).

#### Scenario: A date from the host
- **WHEN** the host calls `await chat.showCard({type: "ask", question: "When?", input: {type: "date"}})`
- **THEN** the calendar card appears, and the promise resolves with `{answer: {text: "<date>"}}` when the user picks a day

### Requirement: Dictation ends with any chat action
Any chat action other than sending the composer (a chip or starter, a card answer or Skip, a run started by the host, New chat) SHALL end a running dictation and drop the dictated words, keeping only the text typed before it. Results that arrive afterwards SHALL be ignored.

#### Scenario: A chip tapped while dictating
- **WHEN** the user is dictating and taps a quick reply or Skip on a card
- **THEN** the microphone turns off, the dictated words leave the composer, and late recognition results are ignored

### Requirement: Connection options
The chat SHALL accept `headers` as an object or as a function of `{kind, url}` (sync or async) called before every request, plus `credentials`, `fetch` (used instead of the global fetch) and `request` (a function of `{kind, url, init}` returning the `{url, init}` to send). `kind` SHALL be `run` for a run and the plugin's name for others (`attachments`, `thread`, `feedback`).

#### Scenario: A refreshed token
- **WHEN** `headers` is `async () => ({Authorization: 'Bearer ' + await getToken()})`
- **THEN** every run and every plugin request carries the current token

#### Scenario: A custom fetch
- **WHEN** `fetch` is set to the host's function
- **THEN** the chat sends every request through it and never calls the global fetch

### Requirement: Own transport
The chat SHALL accept `transport`, a function of the run input and `{signal}` returning an async iterable of AG-UI events, and use it instead of HTTP; when it is not set, an `agent` object, and otherwise `url`, SHALL be used as before. A failure of the transport, `headers`, `fetch` or `request` SHALL end the run with the usual readable error.

#### Scenario: A mock transport
- **WHEN** `transport` yields RUN_STARTED, a text message and RUN_FINISHED
- **THEN** the chat shows the text and makes no network request

### Requirement: Requests through the chat's connection
`ChatApi.request(kind, url, init)` SHALL send a request with the chat's headers, credentials, fetch and request hook, so plugins reach the server the same way as runs.

#### Scenario: A plugin request
- **WHEN** a plugin calls `chat.request('thread', url)` and `headers` adds an Authorization header
- **THEN** the request carries that header

### Requirement: Dictation on the server
`dictation: 'server'` SHALL make the microphone record audio instead of using the browser's recognition: the input is replaced by a live wave with a timer and a cancel button; tapping the microphone again SHALL show "Transcribing…", post the recording to `transcribeUrl` (default: `transcribe` next to the run URL) through the chat's connection, and put the text into the input without sending it (unless `micAutoSend`).

#### Scenario: Dictating through the server
- **WHEN** the user taps the microphone, speaks and taps it again
- **THEN** the chat shows "Transcribing…" and then the recognised text in the input

### Requirement: Cancelling and failures of server dictation
Esc or the cancel button SHALL drop a recording without sending it. An empty result SHALL say nothing was caught; a failed transcription SHALL say so in plain words with "Try again", which posts the same recording again.

#### Scenario: The server is down
- **WHEN** the transcription request fails
- **THEN** the hint says the recording could not be transcribed and offers Try again

### Requirement: Dictation that falls back
`dictation: 'auto'` SHALL use the browser's recognition where it exists and works, and record for the server where it is missing or blocked (the recognition service refused or unreachable); the microphone SHALL show whenever either way is possible.

#### Scenario: A browser without recognition
- **WHEN** the browser has no SpeechRecognition and `dictation` is `auto`
- **THEN** the microphone shows and records for the server

### Requirement: Pasting and dropping files into the composer
When uploads are available (the + button shows), files pasted into the input (a screenshot from the clipboard) or dropped on the composer SHALL be attached exactly as the + button attaches them; a paste without files SHALL stay plain text. The input SHALL grow with its text up to its limit, also after dictation puts text into it.

#### Scenario: A pasted screenshot
- **WHEN** the user presses Cmd+V with a screenshot in the clipboard
- **THEN** the screenshot is uploaded and shown as an attachment of the next message

### Requirement: Messages sent while the assistant answers wait in a queue
A message sent while a turn runs SHALL NOT interrupt it: it SHALL wait last in the log, marked Queued, with Send now, Edit and Remove, and the answer being written SHALL land above it. When the turn ends the queued messages SHALL go one by one, in order; while a question card waits for its answer they SHALL wait too ("Sends after you answer the question"). The input's placeholder SHALL say that Enter queues while the assistant answers.

#### Scenario: A second message while the first is answered
- **WHEN** the user sends "second" while the answer to "first" is still coming
- **THEN** "second" shows below the answer, marked Queued, and is sent by itself when that answer ends

### Requirement: Acting on a queued message
Send now SHALL stop the running answer and send that message next; Edit SHALL put its text back into the input, under any draft there, and take it out of the queue; Remove SHALL take it out with Undo. Only the next queued message SHALL show its actions at rest. The queue SHALL be kept per thread across a reload and cleared by a new chat.

#### Scenario: Send now
- **WHEN** three messages wait and the user taps Send now on the second
- **THEN** the running answer stops, the second message is sent, and the other two keep waiting in order

### Requirement: A paused queue
Stop SHALL pause the queue (its messages say "Paused"), and a failed answer SHALL pause it under its error ("Sends after Try again"). A message sent while the queue is paused SHALL go in behind the waiting ones, and the queue SHALL then go on in order.

#### Scenario: A message after Stop
- **WHEN** the user stops the answer while "two" waits, then sends "three"
- **THEN** "two" is sent first and "three" after it
