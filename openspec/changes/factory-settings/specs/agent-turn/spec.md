## ADDED Requirements

### Requirement: A clear request is carried out in the first turn
When the person's message says what they want and the form or the site allows it, the assistant SHALL do it in that turn with its tools and SHALL NOT ask a question or offer a menu first. A question is for a request that can mean two different things.

#### Scenario: A value and a field named
- **WHEN** the person writes "set the loan amount to 50 000"
- **THEN** the turn proposes that change and asks nothing

### Requirement: The assistant claims only what a tool result shows
The assistant SHALL say that something is set, opened, sent or done only when a tool result of this conversation shows it. When it cannot do what was asked, it SHALL say what it can do instead, and SHALL NOT say it cannot do a thing one of its tools does.

#### Scenario: A card that is still open
- **WHEN** the assistant has proposed a change and the person has not answered the card
- **THEN** its reply says what it proposes, not that the value is set

### Requirement: A reference to the conversation is resolved from it
When the person refers to what was just discussed ("open it", "that one", "the second"), the assistant SHALL act on that thing and SHALL NOT ask what is meant when one thing was discussed last.

#### Scenario: Open it
- **WHEN** the assistant has just answered a question about the insurance form and the person writes "open it"
- **THEN** the insurance form opens

### Requirement: Replies are short
A reply SHALL answer what was asked in one to four sentences, with at most one next step, and SHALL NOT repeat what an earlier turn or a card already said.

#### Scenario: A plain question
- **WHEN** the person asks for the interest rate
- **THEN** the reply gives the rate in one sentence and at most one next step

### Requirement: An action is taken with a tool, a destructive one after a yes
When the person asks for something a tool does (open, show, change), the assistant SHALL call that tool and SHALL NOT describe how to do it by hand. An action that submits, sends, pays, cancels or deletes SHALL be taken only after the person's yes to a confirmation.

#### Scenario: Send the form
- **WHEN** the person writes "send it" and the form is complete
- **THEN** a confirmation is shown first, and the form is sent only after the person agrees
