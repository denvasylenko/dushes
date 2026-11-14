# Spec Delta

## ADDED Requirements

### Requirement: Reply to a part of an answer
Selecting text inside one agent message SHALL show a capsule with Reply and, when dictation is available, a microphone. On a fine pointer the capsule sits above the selection, and on a touch screen under it. There SHALL be no capsule for:
- a selection in the user's own messages, cards, tool steps or the action bar;
- a selection spanning two messages;
- the `reply` option off.

The capsule SHALL hide when the selection is emptied, on a scroll and on Esc.

#### Scenario: A line of an answer
- **WHEN** the user selects "the fee is 2%" in an agent's message with a mouse
- **THEN** a capsule with Reply and a microphone appears above the selection

#### Scenario: Own message
- **WHEN** the user selects text in their own bubble
- **THEN** no capsule appears

### Requirement: The quote in the composer
Reply SHALL put a quote bar at the top of the composer and focus the field. The bar holds a reply icon, the selected text on one line ending in "…" when it is longer, and a close button. The microphone SHALL do the same and start dictation. The close button or Esc SHALL remove the quote. The quote is the selection's plain text with whitespace collapsed, at most 300 characters, cut with "…".

#### Scenario: Esc removes the quote
- **WHEN** a quote is in the composer and the user presses Esc in the field
- **THEN** the quote bar disappears and the panel stays open

### Requirement: The quote travels with the message
Sending with a quote SHALL add `forwardedProps.reply_to = {message_id, quote}` to that run only, where `message_id` is the quoted agent message's id. The user's bubble SHALL show the quote above the text. A tap on the quote SHALL scroll to the quoted message and highlight it briefly. A restored user message with `reply_to` SHALL show its quote too, and `reply_to` SHALL NOT be sent back in `messages`.

#### Scenario: Asking about a line
- **WHEN** the user replies to "the fee is 2%" with "is that per month?"
- **THEN** the run's `forwardedProps.reply_to` is `{message_id: <that answer's id>, quote: "the fee is 2%"}`, and the bubble shows the quote above "is that per month?"

### Requirement: Reply to the whole answer
Reply under an answer, and on a touch screen a swipe left on it by more than 56 px (as in Telegram), SHALL reply to the whole message. The run then carries `forwardedProps.reply_to = {message_id, whole: true}`, with no `quote`. The quote bar and the bubble SHALL show the assistant's name on the first line and the answer's start under it when the answer is in the log, labelled "Reply to the whole answer" for screen readers, and the field SHALL be described by the quote while it is set.

#### Scenario: Swipe on a phone
- **WHEN** the user swipes an answer to the left on a phone and sends "and on Saturday?"
- **THEN** the run's `reply_to` is `{message_id: <that answer's id>, whole: true}` and the bubble shows the assistant's name over the answer's start

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
