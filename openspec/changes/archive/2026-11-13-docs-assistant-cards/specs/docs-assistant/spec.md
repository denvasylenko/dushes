## ADDED Requirements

### Requirement: Answer cards
The docs assistant SHALL answer with short text and cards: code quoted verbatim from the documentation (`show_code`, tabs when there are variants), page cards (`show_pages`), a numbered how-to (`show_steps`) and live gallery cards (`show_card`). Cards SHALL be sent as `CUSTOM docs_card` events after the answer's text.

#### Scenario: A how-to question
- **WHEN** a reader asks how to use Azure OpenAI for the agent
- **THEN** the answer has one or two sentences, a code card whose blocks are exactly the documentation's blocks, and a page card for the models guide

### Requirement: Follow-up questions
Every answer SHALL end with two or three follow-up questions sent as `CUSTOM suggestions`, which the chat shows as chips.

#### Scenario: Tapping a follow-up
- **WHEN** the reader taps a follow-up chip
- **THEN** it is sent as the next question

### Requirement: Conversation limits
The assistant SHALL limit questions per conversation (default 15), per address per minute and per day, and per site per day, and SHALL answer a refused request with a human sentence.

#### Scenario: The sixteenth question
- **WHEN** a conversation sends its sixteenth question
- **THEN** the request is refused with "This chat has reached its limit" and no model is called
