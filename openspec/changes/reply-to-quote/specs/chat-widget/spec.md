# Spec Delta

## ADDED Requirements

### Requirement: Reply to a part of an answer
As in the Claude app, replying takes two steps. Selecting text inside one agent message SHALL show a small capsule with Reply; a scroll, Esc or a tap elsewhere SHALL take it away. Reply SHALL open a reply window in its place, with the quote on one line (ending in "…"), a field "Reply to <the assistant's name>" that takes the focus, a microphone that dictates into that field (Cmd or Ctrl+D), and Add to chat.

#### Scenario: A line of an answer
- **WHEN** the user selects "the fee is 2%" in an agent's message with a mouse
- **THEN** a capsule with Reply appears above the selection, and Reply opens a window with the quote, a field "Reply to Assistant" and Add to chat

### Requirement: Where the capsule and the window sit
The capsule and the reply window SHALL sit above the selection on a fine pointer and under it on a touch screen, clear of the system's own selection menu.

#### Scenario: On a phone
- **WHEN** the user selects a line on a touch screen
- **THEN** the Reply capsule appears under the selection

### Requirement: The reply window follows its text
The reply window SHALL move with the quoted text when the log scrolls, never pinned to an edge of the panel, and stay open. Esc or a tap elsewhere SHALL close it, keeping anything typed as a quote with its reply in the composer.

#### Scenario: Scrolling while typing
- **WHEN** the user has typed in the window and scrolls the log
- **THEN** the window moves with the quoted answer and stays open

### Requirement: No reply window
There SHALL be no capsule or reply window for a selection in the user's own messages, cards, tool steps or the action bar, for a selection spanning two messages, or with the `reply` option off.

#### Scenario: Own message
- **WHEN** the user selects text in their own bubble
- **THEN** no window appears

### Requirement: Send or collect a reply
In the reply window, Enter and Add to chat SHALL put the quote into the composer, under the quotes already there, with what was typed as its reply, and send nothing. Enter in the composer SHALL send the message with every collected quote. A quote is the selection's plain text with whitespace collapsed, at most 300 characters, cut with "…".

#### Scenario: Enter in the window
- **WHEN** the user types "is that per month?" in the window and presses Enter
- **THEN** the window closes and the composer shows the quote as a tile with "With reply", nothing sent yet

### Requirement: Several quotes in the composer
The composer SHALL show each collected quote as its own grey tile, one under another, in the order collected, at most ten. A tile holds a reply icon, the quote in quotation marks on one line, "With reply" when it carries a reply (a tap shows it), and a close button. The close button SHALL remove that quote, and Esc in the field the last one. The field SHALL be described by the tiles while any is there.

#### Scenario: Two quotes, one with a reply
- **WHEN** the user adds "the fee is 2%" with "per month?" and then "the term is 36 months" with nothing typed
- **THEN** two tiles show, the first with "With reply", and one message sends both

### Requirement: The quotes travel with the message
Sending SHALL add `forwardedProps.reply_to` to that run only: a list of `{message_id, quote, note?}` or `{message_id, whole: true, note?}`, in order. The user's bubble SHALL show every quote above the text, each with its reply under it. A tap on a quote SHALL scroll to the quoted message and highlight it briefly. When every quote carries a reply, the message MAY have no text of its own; the run then still carries a short user text, which the bubble does not show.

#### Scenario: Asking about a line
- **WHEN** the user replies to "the fee is 2%" with "is that per month?"
- **THEN** the run's `reply_to` is `[{message_id: <that answer's id>, quote: "the fee is 2%"}]`, and the bubble shows the quote above "is that per month?"

### Requirement: Restored replies
A restored user message with `reply_to`, as a list or as one object from an older server, SHALL show every quote and its reply. `reply_to` SHALL NOT be sent back in `messages`.

#### Scenario: After a reload
- **WHEN** the history returns a user message with two quotes, the first with a reply
- **THEN** its bubble shows both quotes in order and the reply under the first

### Requirement: Reply to the whole answer
Reply under an answer, and on a touch screen a swipe left on it by more than 56 px (as in Telegram), SHALL reply to the whole message. It adds `{message_id, whole: true}` (no `quote`) to the collected quotes. Its tile and the bubble SHALL show the assistant's name on the first line and the answer's start under it when the answer is in the log, labelled "Reply to the whole answer" for screen readers, and the field SHALL be described by the quote while it is set.

#### Scenario: Swipe on a phone
- **WHEN** the user swipes an answer to the left on a phone and sends "and on Saturday?"
- **THEN** the run's `reply_to` is `[{message_id: <that answer's id>, whole: true}]` and the bubble shows the assistant's name over the answer's start

### Requirement: A swipe that does not reply
A swipe SHALL NOT reply when it starts within 24 px of the screen's edge, while text is selected, in a card, code, a table or an image, or vertically.

#### Scenario: Swiping the other way
- **WHEN** the user swipes an answer to the right, or swipes in from the screen's edge
- **THEN** no reply starts, and the system's back gesture keeps working

### Requirement: Long messages fold
A user's bubble taller than `collapseLines` lines (default 8; 0 turns folding off) SHALL show its start and its quote, with the bottom fading into the bubble's colour and "Show more" under it. "Show more" SHALL show the whole message, and "Show less" fold it again, keeping the button in view. The button SHALL carry `aria-expanded` and `aria-controls`. A message only one or two lines over SHALL NOT fold. Agent answers SHALL fold only with `collapseAnswers` on (default off).

#### Scenario: A pasted text
- **WHEN** the user sends forty lines of pasted text
- **THEN** the bubble shows its first eight lines fading out and "Show more", and a tap shows all forty lines with "Show less"

### Requirement: Cards never fold
Cards SHALL never fold like long messages. A finished card SHALL be quieter by its shape (one result line), with its text, its check mark and Undo at full contrast, never by opacity.

#### Scenario: Fields filled in
- **WHEN** the user taps "Fill in 3 fields"
- **THEN** the card becomes one line "Filled in · Loan type, Loan amount, Term" with Undo, at full contrast and with no fade over it

### Requirement: How the mic turns speech into text
The `voice` option SHALL choose:
- `auto` (default): the server when it transcribes (its restore returns `transcription: true`, or `transcribeUrl` is set); without one, the browser's own recognition in Chromium on a computer and on Android, and otherwise (iPhone, Safari, Firefox, or a blocked service) recording for the server;
- `browser`: the browser only, and no mic where it has none;
- `server`: always the server;
- `off`: no mic.

#### Scenario: An iPhone
- **WHEN** `voice` is `auto` and the visitor opens the chat on an iPhone
- **THEN** the mic records and the server transcribes, instead of the browser's recognition

### Requirement: The old dictation option
The old option `dictation` SHALL still apply when `voice` is left at `auto`. The documentation of `voice` SHALL say that Chrome's recognition sends the audio to Google, and that sites with sensitive data should use `server`.

#### Scenario: An older page
- **WHEN** a page sets only `dictation="browser"`
- **THEN** the mic uses the browser's recognition, as before

### Requirement: Shortcut tooltips
The composer's buttons SHALL show a tooltip after about 500 ms of mouse hover and at once on keyboard focus: one row per action, its keys on the right as key caps. The send button lists Send (Enter) and New line (Shift+Enter), or Stop while the assistant works; the microphone lists Dictate (Cmd or Ctrl+D), which SHALL work in the field. Keys SHALL be written as symbols on a Mac and as words elsewhere. There SHALL be no tooltip on a touch screen or with `shortcutHints` off.

#### Scenario: Hovering Send on a Mac
- **WHEN** the user rests the mouse on the send button for half a second
- **THEN** a dark plate reads "Send ↵" and "New line ⇧ ↵"

### Requirement: The composer's attachments
A new attachment SHALL grow in from 0.92 and fade in over about 200 ms, the others sliding to their place; a removed one SHALL shrink away first. With a mouse its remove button SHALL appear on hover or keyboard focus; on a touch screen it SHALL stay visible, with a 44 px target. Reduced motion SHALL drop the animations.

#### Scenario: Removing a photo
- **WHEN** the user taps the x on the first of two attached photos
- **THEN** it shrinks away and the second slides into its place, with no jump

### Requirement: The composer's shadow
The composer SHALL carry a soft shadow, a little stronger when focused and fainter in dark, set by `composerShadow` (`soft`, `raised`, `none`) or by `--agui-composer-shadow` and `--agui-composer-shadow-focus`.

#### Scenario: A flat page
- **WHEN** a page sets `composer-shadow="none"`
- **THEN** the composer has no shadow, focused or not

### Requirement: One dictation at a time
The composer and the reply window SHALL each have a microphone, and both SHALL stay visible while dictation is available. Pressing one while the other dictates SHALL stop the other first; the words it already put in its field SHALL stay. With `voice: off` there SHALL be no microphone in either.

#### Scenario: From the composer to the window
- **WHEN** the user dictates "and the term" in the composer, opens a reply window and presses its microphone
- **THEN** the composer keeps "and the term", its microphone is idle, and the window's field receives the new dictation

