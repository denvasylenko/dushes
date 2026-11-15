## ADDED Requirements

### Requirement: Voice mode is off without the code
The demo host SHALL offer its voice routes only when a voice code is set on the host, and SHALL require a pass given for the right code on every voice route. Without the code set, or without a pass, the widget SHALL show no voice mode and the routes SHALL answer as if they did not exist.

#### Scenario: A visitor without the code
- **WHEN** a visitor opens a demo page and has not entered the code
- **THEN** the chat is as it always was, and a request to start a voice conversation is refused

### Requirement: The voice is not the agent
In voice mode the speech model SHALL pass what the person asked to the Dushes agent and speak its result; it SHALL NOT fill fields, open pages or answer about the business on its own. A voice turn SHALL be an ordinary turn of the conversation: the same agent, rules, cards and transcript as in chat.

#### Scenario: A question asked aloud
- **WHEN** the person asks aloud what car insurance costs
- **THEN** the Dushes agent answers it as it would in chat (nothing opens), the steps and the answer appear in the orb view, and the voice says the answer

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

### Requirement: A change is never applied by voice alone without a yes
A field-change card in voice mode SHALL be applied only after the person accepts it, by a tap or by an explicit spoken yes; a consent tick SHALL be accepted by a tap only.

#### Scenario: A consent
- **WHEN** the agent proposes ticking a consent and the person says "yes"
- **THEN** the consent is not ticked, and the card asks for a tap
