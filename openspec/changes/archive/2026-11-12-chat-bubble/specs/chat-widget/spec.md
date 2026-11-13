## ADDED Requirements

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
