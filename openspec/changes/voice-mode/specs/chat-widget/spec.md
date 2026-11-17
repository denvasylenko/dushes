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
The orb SHALL show one of: listening, thinking while a turn runs (smaller, lifted, faster), speaking (from the sound level or `spoken` events, never from audio arriving), and silent (smaller, grey, still). A press SHALL stop the turn that runs or quiet the voice that speaks; while listening it SHALL turn the microphone off, while silent on.

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
While the person speaks, `hearing` deltas SHALL show as one faint line above the orb, not as a message; `heard` SHALL put the whole phrase into the conversation as one message. The voice's own words with no agent answer behind them SHALL be an assistant message, growing word by word. After `result`, what the voice says SHALL NOT be written again: an answer is one message, the written one. While a turn runs, the voice's words SHALL show under the orb as its status.

#### Scenario: Small talk
- **WHEN** `hearing` gives "Hello there" and `spoken` gives "Hi! How can I help?" with no `heard` and no `result`
- **THEN** the conversation shows "Hello there" as the person's message and "Hi! How can I help?" as the assistant's

### Requirement: The microphone is never on without the orb
A voice conversation SHALL end, with the microphone released, when the chat is closed, removed from the page, a new chat starts, the page is left, or the start is cancelled while the browser still asks for the microphone (a stream that arrives late SHALL be stopped and a session created late SHALL be ended). The orb's box SHALL keep one size in every state, so the conversation does not move.

#### Scenario: A tap during the permission prompt
- **WHEN** the person taps the microphone button while the browser asks for the microphone, then allows it
- **THEN** no microphone stays open, no session is left running, and the button starts voice when tapped again

### Requirement: Filling without a card
A `set_fields` card whose payload has `quiet: true` SHALL be applied, in voice mode and in the plain chat alike, through the host's form as soon as it arrives, exactly as if the person had accepted it, without a card that waits: the conversation SHALL keep its result line with Undo. A card without the mark SHALL be drawn and wait. A card drawn from a restored conversation SHALL NOT be applied by the mark.

#### Scenario: A value the person said
- **WHEN** voice mode is on and a `set_fields` card with `quiet: true` arrives for Amount
- **THEN** the field is filled with no tap, the run is resumed as accepted, and the conversation shows the result line with Undo

#### Scenario: A typed yes in the plain chat
- **WHEN** the person types "yes" instead of tapping a card, and the same values come again in a card with `quiet: true`
- **THEN** the fields are filled at once, with the result line and Undo, and no second card waits

### Requirement: The voice's own echo is not the person
The microphone SHALL be asked for with echo cancelling, noise suppression and automatic gain. A `heard` text of four words or more that is, word for word, part of what the voice said or the agent wrote in the last 15 seconds SHALL be taken as the voice heard through the speakers: it SHALL NOT be sent or shown as the person's message. A shorter text SHALL always be sent.

#### Scenario: The question comes back
- **WHEN** the voice says "Choose the date and time of the booking" and the stream then sends `heard` with the same words
- **THEN** no message is sent and none of the person's is drawn

### Requirement: A spoken yes or no answers the waiting card
When a `heard` event carries `answers` with a card's id and `accepted`, the chat SHALL answer that card exactly as its own buttons do (accepted: the Fill or Confirm path; not accepted: the Reject or Cancel path) and SHALL NOT send the words as a new message; the words SHALL be shown as the person's message. A spoken yes SHALL also tick a consent in that card. For a question card (type `ask`), or a card that is not on the screen, the words SHALL go as an ordinary message.

#### Scenario: Yes to a field-change card
- **WHEN** a field-change card waits and the person says "yes please"
- **THEN** the fields are filled and the turn resumes as after the Fill button, and no new message is sent

#### Scenario: No to a card
- **WHEN** a card waits and the person says "no"
- **THEN** the card is rejected as by its Reject button

### Requirement: Leaving the page ends the voice conversation
The chat SHALL end the voice conversation on the host when the page is left (closed, navigated away or reloaded) and, on a touch device, when the page goes to the background.

#### Scenario: The page is reloaded
- **WHEN** the person reloads the page during a voice conversation
- **THEN** the host receives the end of that conversation

### Requirement: Speaking over the voice
On an `interrupted` event the chat SHALL fade the voice's sound out in about 150 ms and then mute it, drop the rest of that answer (neither written nor lit), and show the orb listening. The next `heard` or `result`, or 3 s without the person's words, SHALL unmute the voice, so it is never left muted.

#### Scenario: The person cuts in
- **WHEN** the voice is speaking and `interrupted` arrives
- **THEN** the sound fades out within about 150 ms, later `spoken` words of that answer are not shown, and the orb listens

### Requirement: One utterance is one message
What the person says SHALL reach the conversation as one message per utterance, however the voice's words are interleaved with theirs: `hearing` SHALL only grow the faint line, and `spoken` SHALL NOT turn a phrase still being said into a message nor start a new assistant message in the middle of one. A heard line longer than its width SHALL fade at its start, never be cut hard.

#### Scenario: The voice says a word while the person speaks
- **WHEN** `hearing` "Yeah, yeah", `spoken` "Okay.", `hearing` ". Set it" arrive in that order while an answer is read out
- **THEN** the conversation gains no message from them, the faint line reads "Yeah, yeah. Set it", and `heard` then adds it as one message

### Requirement: The answer lights up as it is spoken
While the voice speaks an answer, the written answer SHALL be dim with the words said so far bright, moving at a speaking pace and only while there is sound. When the voice is done or stopped, the answer SHALL be plain text again. Where the browser cannot paint a text range, nothing SHALL be dimmed.

#### Scenario: The voice reads the answer
- **WHEN** the voice has said the first words of the answer
- **THEN** those words are bright in the written answer and the rest is dim

### Requirement: A light at the bottom says the state
In voice mode a soft light SHALL rise from the bottom edge of the chat: the voice colour while listening (stronger with the person's voice), a warm colour while the voice speaks, faint while a turn runs, none in silent mode.

#### Scenario: The voice speaks
- **WHEN** the voice speaks an answer
- **THEN** the light at the bottom is warm

### Requirement: The look of voice mode
The orb SHALL be a sky of the voice colour (the host's accent) with a white cloud bank going round. It SHALL carry no mark at rest; the stop mark shows only under the pointer, the focus or a press. While voice mode is on, the header SHALL say "Voice" or "Silent", the message box SHALL show a ring that fills with the person's voice, its send and stop buttons SHALL show only while a message is typed, and a short conversation SHALL sit low, by the orb.

#### Scenario: The agent is working
- **WHEN** a turn runs in voice mode and nothing is typed
- **THEN** the orb turns faster, the turn's step shows in the conversation above the answer, the orb has no square in it, and the message box shows no stop button of its own

#### Scenario: The line under the orb names the state
- **WHEN** a turn runs, and later the voice speaks the answer
- **THEN** the line says "Thinking", then "Speaking", and "Listening" only while the chat listens
