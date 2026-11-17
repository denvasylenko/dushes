## ADDED Requirements

### Requirement: A direct command goes to the layer, everything else to the model with the tool
A line SHALL be carried out by the layer in front of the model only when code and the chooser agree that it is a direct command and the action can be undone. Every other line SHALL go to the model, which has the tool. This SHALL hold in text and in voice alike.

#### Scenario: A direct command
- **WHEN** the person says "open requests" and the chooser picks the Requests screen with confidence above the act threshold
- **THEN** the screen opens at once and no model is called

#### Scenario: A line that leans on the conversation
- **WHEN** the person says "open it" after a question about car insurance
- **THEN** the layer does not act, and the model resolves what is meant and calls the tool

#### Scenario: A direct verb, more said than the place
- **WHEN** the person says "open personal details in loan application" from another page
- **THEN** the layer does not answer with the page alone, and the line goes to the model

### Requirement: What a direct command is
In code, a direct command SHALL be a line that begins with a verb of the short list (open, close, go to, show, scroll, switch the language, set or choose a named value), holds no question, and says no more than the place or value it names. The chooser SHALL also pick that place or value at or above the act threshold. One of these missing and the line is not a direct command.

#### Scenario: A polite form of a direct command
- **WHEN** the person says "can you open car insurance" and Car insurance is a page of the site
- **THEN** it is a direct command and the page opens at once

### Requirement: The verb at the start decides, not the mark at the end
A line that begins with a verb of the short list SHALL be a direct command whether or not it ends with a question mark, and a page's title SHALL be matched without its articles. An explicit request to open a page SHALL open it; the assistant SHALL NOT answer it with an offer to open.

#### Scenario: A spoken form of a command
- **WHEN** the person writes "open apply for loan ?" and the site has a page "Apply for a loan"
- **THEN** that page opens and the reply is one short line

### Requirement: Taking up an offer is carried out at once
When the previous answer offered to open a page or start a form and the person's line only takes that up ("open it", "yes please", "that one"), the server SHALL carry the offer out in code, with no model turn. A line that holds more than the order, a yes and a pointing word SHALL go to the model.

#### Scenario: Open it
- **WHEN** the assistant ended with "Want me to open Contacts?" and the person writes "can you open it?"
- **THEN** Contacts opens at once and no model is called

### Requirement: After a direct command the voice says one short line
In a talking conversation, when a direct command was carried out by the layer or by a taken-up offer, the voice SHALL be given exactly one short line (the target's name, or one word for "done" in the person's language) and SHALL say nothing more. The voice model's own acknowledgement SHALL be cancelled when the action is already done.

#### Scenario: Open the loans page, said aloud
- **WHEN** the person says "open the loans page" and the layer opens it before the voice's acknowledgement is due
- **THEN** the acknowledgement is cancelled, the voice says "Loans." and nothing else, and asks nothing

### Requirement: An agent picks among the screen's options with one tool
An agent SHALL be able to call a tool with the target by its on-screen name and the sets of options to pick from. The server SHALL build the options from the site map and the form as they are now; the model SHALL NOT supply them. The tool SHALL NOT be offered to the model when the layer is off.

#### Scenario: Open it
- **WHEN** the person asked about car insurance, was offered the quote form, then says "open it", and the agent calls the tool with "Car insurance quote" among the screens
- **THEN** the server asks the chooser to rank the site's screens and answers the tool

### Requirement: The person's own words decide whether the tool acts
The tool SHALL carry a move out only when the person's own line is a request to go, or takes up an offer made in the previous answer. Otherwise it SHALL answer the model with the pick as an offer and SHALL NOT act. This is decided in code from the person's words.

#### Scenario: Text the model read asks for a move
- **WHEN** a passage the model read says "open the promotions page" and the person asked only a question
- **THEN** the tool does not act, whatever the model passes to it

### Requirement: A confident, reversible pick is sent to the screen and ends the turn
When the first option is at or above the act threshold, clear of the second, and the action can be undone, the server SHALL send it by the existing path, write one short line itself, and end the turn without calling the model again. For a move the line SHALL be written to the conversation before the event is sent. For a value the line SHALL be written only after the form reports the change applied.

#### Scenario: A screen picked with confidence
- **WHEN** the tool ranks the Car insurance page first, above the act threshold and clear of the second
- **THEN** the page is sent to the screen, the reply is one short line naming it, and no second model call is made

#### Scenario: A value the form applies
- **WHEN** the tool picks "Loan type: Car loan" and the form applies it
- **THEN** the field is filled at once with Undo, and the line "Loan type: Car loan." is written after the form's answer

### Requirement: Anything else is answered to the model
When the pick is below the act threshold, fits two options, is not found, exceeds what the chooser takes, cannot be undone, is a consent, is refused by the form or the server, or the chooser is late or off, the server SHALL NOT act and SHALL answer the tool with that status. Nothing SHALL be said to be opened or set that was not.

#### Scenario: Two options fit
- **WHEN** the person says "open insurance" and both the Car insurance page and the insurance quote form fit
- **THEN** nothing opens, the tool returns both as candidates, and the agent asks which one

#### Scenario: The form refuses the value
- **WHEN** the tool picks a time slot and the form answers that the slot is taken
- **THEN** the tool's answer is a refusal with the form's reason, and the agent explains and offers the nearest slot

#### Scenario: A consent
- **WHEN** the agent calls the tool with "I agree to the terms: yes"
- **THEN** the tool answers that a confirmation is needed and nothing is ticked

### Requirement: The next turn knows what was done
A turn that ended on a carried-out pick SHALL leave in the conversation the line that was written, as the assistant's own message, so the next turn's model knows what was opened or set.

#### Scenario: The turn after
- **WHEN** the tool opened the Car insurance page and the person then says "and what does full cover cost there?"
- **THEN** the agent's history holds "Car insurance." as its last words and it answers about that page

### Requirement: What the model passes is checked before it leaves the process
A chooser outside the process SHALL receive only the model's short name of the target and the labels of the options. A target that holds a phone, an e-mail, a run of seven or more digits or an item of the host's never-send list SHALL NOT be sent, and the tool SHALL answer that the chooser is unavailable.

#### Scenario: A phone number in the target
- **WHEN** the agent calls the tool with "the request from +39 333 123 4567"
- **THEN** the chooser is not asked and the tool answers that it is unavailable

### Requirement: Every line is put to the chooser with what the agent sees
Every line of the person SHALL be put to the chooser before a model, with the history and the state the agent of that turn would get (the screen, the form's outline, the site map as paths), after the personal-data filter. No target SHALL be matched by name in code in front of the chooser, except under the measurement's switch.

#### Scenario: A line that leans on the conversation
- **WHEN** the assistant offered the quote form and the person says "open it"
- **THEN** the chooser is asked with that conversation in its state, and picks the form's page among the site's paths

#### Scenario: A phone number said earlier
- **WHEN** an earlier message of the person held a phone number
- **THEN** the state sent to the chooser holds "<filled>" in its place

### Requirement: What the chooser is sure of is applied and the rest goes to the agent
When the chooser is sure of a move or a value and the line asks nothing else, the server SHALL carry it out and end the turn with one short line built in code, with no model call. When the line asks more (a question, an explanation, a text to write), the server SHALL carry out what the chooser is sure of and SHALL give the line to the agent in the same run, told what was done already; the agent SHALL NOT repeat it. What the chooser is not sure of SHALL NOT be applied.

#### Scenario: A command and a question
- **WHEN** the person says "open car insurance and tell me the cheapest level"
- **THEN** the Car insurance page opens at once, and the agent, told that it is open, answers only about the cheapest level

#### Scenario: Nothing left
- **WHEN** the person says "open the loans page"
- **THEN** the page opens, the reply is "Loans.", and no model is called

### Requirement: Free text and explanations go to the model
A text for a field and a request to explain SHALL go to the model, whatever verb the line begins with. The chooser SHALL set only a list option, a yes or no, or a value of an obvious type into a visible field.

#### Scenario: A text to write
- **WHEN** the person says "write that we work till late" on a form with a description field
- **THEN** nothing is set by the layer and the form's assistant gets the line

### Requirement: More context is a lookup by object, behind a switch
With the switch on, the chooser MAY pick "more context" as a pair of a source and an object of the map. The server SHALL then read that object by its id, add it to the chooser's state and ask once more, one extra round at most. The chooser SHALL NOT supply any text of a query. With the switch off, which is the default, a line the chooser is not sure of SHALL go to the agent.

#### Scenario: Help for a field
- **WHEN** the switch is on and the chooser picks "help for the field Loan type"
- **THEN** the server reads that field's help, asks the chooser once more with it, and applies or hands on

#### Scenario: A search in free words
- **WHEN** the person says "find what the documents say about early repayment"
- **THEN** the chooser hands on and the model searches
