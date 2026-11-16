## ADDED Requirements

### Requirement: Voice mode is off without the code
The demo host SHALL offer its voice routes only when at least one voice code is set on the host, SHALL keep one code per person, and SHALL require a pass given for a right code on every voice route. Usage SHALL be counted per code. Without the code set, or without a pass, the widget SHALL show no voice mode and the routes SHALL answer as if they did not exist.

#### Scenario: A visitor without the code
- **WHEN** a visitor opens a demo page and has not entered the code
- **THEN** the chat is as it always was, and a request to start a voice conversation is refused

### Requirement: The voice is not the agent
In voice mode the speech model SHALL pass what the person asked to the Dushes agent and speak its result; it SHALL NOT fill fields, open pages or answer about the business on its own. A voice turn SHALL be an ordinary turn of the conversation: the same agent, rules, cards and transcript as in chat.

#### Scenario: A question asked aloud
- **WHEN** the person asks aloud what car insurance costs
- **THEN** the Dushes agent answers it as it would in chat (nothing opens), the steps and the answer appear in the orb view, and the voice says the answer

### Requirement: The answer is spoken as it is written
The server SHALL give the voice each whole sentence of the agent's answer once the next sentence has begun, without waiting for the turn to end, and the rest when the turn ends. A single sentence followed by a step, and a sentence taken back and written again, SHALL NOT be spoken twice.

#### Scenario: An answer of three sentences
- **WHEN** the agent has written the first sentence of its answer and begun the second
- **THEN** the voice is given the first sentence at once, and the other two when they are written

### Requirement: No key reaches the browser
The browser SHALL connect its audio through the host: the host creates the call with its own key and returns only the connection answer. No API key, long or short lived, SHALL be sent to the browser.

#### Scenario: Starting a conversation
- **WHEN** the widget starts a voice conversation
- **THEN** it sends its connection offer to the host and receives the answer, and holds no key

### Requirement: Voice has its own limits
The host SHALL keep a daily budget for voice, separate from the chat demos, counted from the usage reported for each response; SHALL end a conversation at its time limit or its money limit, whichever comes first; and SHALL allow a fixed number of voice conversations at once. When a limit is reached the person SHALL be told, and the chat SHALL keep working.

#### Scenario: The day's voice budget is used up
- **WHEN** the voice budget for the day is spent and someone with the code starts a conversation
- **THEN** the start is refused with a reason the widget shows, and typed chat works as before

### Requirement: Speaking over the answer stops it
When the person speaks while the voice is answering, the voice SHALL stop, and the agent's turn in progress SHALL be stopped on the server.

#### Scenario: An interruption
- **WHEN** the person says "wait, not that one" while an answer is being spoken
- **THEN** the speech stops and the turn in progress is cancelled before the new request is taken

### Requirement: What the person said is filled without a card
In voice mode a value the person said aloud in this conversation SHALL be applied to its field without a card, through the host's form, and shown as a short line with Undo. A card SHALL be shown only when a confirmation is needed: a consent, an action that cannot be undone, a value the person did not say, a value that replaces one typed by hand, a value the form refused, or a choice the agent cannot make. In chat mode nothing changes.

#### Scenario: A term said aloud
- **WHEN** the person says "let's try 36" for the loan term
- **THEN** the field is filled, the voice says so, a line with Undo appears, and no card is shown

#### Scenario: A value from a document
- **WHEN** the agent reads an income figure from an uploaded document and proposes it
- **THEN** a card asks for confirmation before the field is filled

### Requirement: A name is read back, never filled quietly
In voice mode a free-text value with letters in it (a first or last name, an e-mail, a street, a company) SHALL NOT be filled without a card, because speech recognition mishears such words. The voice SHALL read the value back as it was heard and ask whether it is right, offering to have it spelled. A number, a date and an option of a list that the person said stay quiet.

#### Scenario: A surname heard wrong
- **WHEN** the person says their last name and it is heard as "Kovalchik"
- **THEN** the voice says "I heard Last name: Kovalchik. Is that right? If not, spell it for me", and nothing is filled until they answer

### Requirement: A waiting card is asked and answered aloud
When a turn ends on a card that waits for the person, the voice SHALL ask the card's own question aloud and SHALL NOT send the person to the screen. A plain spoken yes or no while a card waits SHALL be the answer to that card: yes applies it, no rejects it, and the agent goes on aloud. A consent is applied the same way, by the person's explicit yes to the direct spoken question; it is never filled quietly. Silence SHALL NOT end a conversation while a card waits.

#### Scenario: A date the agent assembled
- **WHEN** the person says "I was born on the first of July, nineteen ninety" and the agent proposes the date on a card
- **THEN** the voice asks whether to fill in 1 July 1990, and the person's "yes, please" fills the field with no tap

#### Scenario: A consent
- **WHEN** the agent proposes ticking a consent and the voice asks the question aloud
- **THEN** the consent is ticked only after the person's spoken yes to that question, or a tap

### Requirement: Silent mode
The voice mode SHALL have a silent switch (the crossed-out microphone): while it is on the microphone SHALL be off, the person types, and the agent SHALL NOT speak and SHALL answer in short text. No speech session SHALL run while it is on. The switch SHALL hold for the conversation.

#### Scenario: The person turns the sound off
- **WHEN** the person taps the crossed-out microphone and types a question
- **THEN** the answer appears as short text under the orb and nothing is spoken
