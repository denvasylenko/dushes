## ADDED Requirements

### Requirement: Voice mode is there only when the host turns it on
A chat without `voice-mode` (the option `voiceMode`) SHALL show no trace of voice mode and SHALL NOT fetch its file. With it, the chat SHALL load the voice mode as its own on-demand file and add the row "Experimental voice mode" to its + menu. The main file of the one-script build SHALL stay within its size budget.

#### Scenario: A host without voice
- **WHEN** a page shows `<agui-chat>` without `voice-mode`
- **THEN** the + menu has no voice row, the message box has no orb, and `agui-chat.voice.js` is not requested

### Requirement: The code opens voice mode once
The voice row SHALL open a sheet that asks for the person's access code and posts it to the host's `unlock` route. A right code SHALL be answered by a small orb in the message box, where the microphone was, and its pass SHALL be kept for the browser session and sent only in the `X-Voice-Pass` header. A wrong code, a host without voice (404) and no connection SHALL each say so in the sheet. A pass the host no longer accepts SHALL bring the sheet back.

#### Scenario: A wrong code
- **WHEN** the person enters a code the host refuses
- **THEN** the sheet says "That code did not work", the field is marked, and no orb appears

### Requirement: A voice conversation is the chat itself
Starting voice SHALL ask for the microphone, connect to the host's `session` route with the chat's own thread id, and follow its event stream. Each `heard` text SHALL be sent as the person's ordinary message in that thread, so the answer, its steps and its cards are the chat's own. The conversation SHALL stay on screen; an orb SHALL sit above the composer for as long as voice mode is on.

#### Scenario: The person speaks
- **WHEN** the stream sends `heard` with "One and a half million for four years"
- **THEN** that text appears as the person's message and a turn runs as if it had been typed

### Requirement: The orb says what is happening
The orb SHALL show one of: listening, thinking while a turn runs (smaller, lifted, faster, the turn's step under it), speaking (from the sound level or `spoken` events, never from audio arriving), and silent (smaller, grey, still). A press SHALL stop the turn that runs or quiet the voice that speaks; while listening it SHALL turn the microphone off, while silent on.

#### Scenario: The voice talks
- **WHEN** `spoken` events arrive
- **THEN** the orb shows speaking, and returns to listening about a second after the last one

### Requirement: Silent mode and leaving
The microphone button beside the composer SHALL be silent mode: it ends the conversation with the voice (`end`), stops the microphone and leaves the chat working in text; pressed again it starts voice again. The close button SHALL leave voice mode with the conversation untouched. While a message is typed, both buttons SHALL step aside and the composer SHALL take the row. Leaving the page SHALL end the conversation with the voice.

#### Scenario: The microphone button
- **WHEN** the person presses the microphone button during a voice conversation
- **THEN** the host's `end` route is called, the microphone is released, the orb turns grey and still, and typing works as before

### Requirement: The reason voice ended is said
When the host ends or refuses a voice conversation (the limit of one conversation, a silence, the day's budget, another conversation going on, a lost connection, a refused microphone), the chat SHALL say why in one line in the conversation, in the chat's language, and fall back to silent mode.

#### Scenario: The limit
- **WHEN** the stream sends `ended` with reason "time"
- **THEN** the conversation gets the line "Voice ended: the limit for one conversation" and the orb is silent

### Requirement: Everything said goes into the conversation
While the person speaks, `hearing` deltas SHALL grow their message in the conversation; `heard` SHALL replace it with the ordinary message. The voice's own words with no agent answer behind them SHALL be an assistant message, growing word by word. After `result`, what the voice says SHALL NOT be written again: an answer is one message, the written one. While a turn runs, the voice's words SHALL show under the orb as its status. There SHALL be no transcript strip outside the conversation.

#### Scenario: Small talk
- **WHEN** `hearing` gives "Hello there" and `spoken` gives "Hi! How can I help?" with no `heard` and no `result`
- **THEN** the conversation shows "Hello there" as the person's message and "Hi! How can I help?" as the assistant's

### Requirement: The microphone is never on without the orb
A voice conversation SHALL end, with the microphone released, when the chat is closed, removed from the page, a new chat starts, the page is left, or the start is cancelled while the browser still asks for the microphone (a stream that arrives late SHALL be stopped and a session created late SHALL be ended). The orb's box SHALL keep one size in every state, so the conversation does not move.

#### Scenario: A tap during the permission prompt
- **WHEN** the person taps the microphone button while the browser asks for the microphone, then allows it
- **THEN** no microphone stays open, no session is left running, and the button starts voice when tapped again

### Requirement: Filling without a card
In voice mode a `set_fields` card whose payload has `quiet: true` SHALL be applied through the host's form as soon as it arrives, exactly as if the person had accepted it, without a card that waits: the conversation SHALL keep its result line with Undo. A card without the mark SHALL be drawn and wait, and outside voice mode the mark SHALL change nothing.

#### Scenario: A value the person said
- **WHEN** voice mode is on and a `set_fields` card with `quiet: true` arrives for Amount
- **THEN** the field is filled with no tap, the run is resumed as accepted, and the conversation shows the result line with Undo
