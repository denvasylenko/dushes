## ADDED Requirements

### Requirement: A choice is made before the agent
When the layer is on, a typed or spoken phrase SHALL first be put to a chooser as a choice among options the package generates from the form and the screen map. A pick with confidence at or above the threshold, made within the deadline, SHALL be carried out without an agent turn.

#### Scenario: A screen named aloud
- **WHEN** the person says "open requests" and the screen map has a screen labelled Requests
- **THEN** that screen opens and no agent turn runs

### Requirement: Without a pick the turn goes to the agent
When the chooser returns none, a confidence below the threshold, an error, or nothing within the deadline, or when the layer is off, the turn SHALL go to the agent exactly as it does without the layer. The layer SHALL be off unless a host turns it on.

#### Scenario: The chooser is late
- **WHEN** the chooser has not answered within 300 ms
- **THEN** the agent takes the turn and the person sees no error

### Requirement: Questions are generated from the form and the screen map
The layer's questions SHALL be generated: a dropdown or radio field becomes a choice over its options, a date field a choice of today, tomorrow, the day after or a weekday, a checkbox a yes / no question, and the screens and the elements of the current screen a choice. A question SHALL hold at most 255 options.

#### Scenario: A checkbox
- **WHEN** the form has a checkbox "High chair" and the person says "with a high chair"
- **THEN** the question for that field is a yes / no question and the answer turns the checkbox on

### Requirement: The supplier is behind one interface
Every chooser SHALL implement one contract: a phrase, its language, a question with its options and the screen go in; an option's id or none, and a confidence, come out. A host's code, its settings and its logs SHALL NOT hold a supplier's name; the supplier is one internal setting.

#### Scenario: Changing the chooser
- **WHEN** the internal setting is changed from one chooser to another
- **THEN** no host code changes and the same phrases are answered through the same contract

### Requirement: The layer only looks and makes reversible edits
By itself the layer SHALL carry out only navigation, showing, and a field change that can be undone. An action that submits, sends, pays, cancels or deletes SHALL NOT be carried out by the layer: it goes to the agent and its confirmation.

#### Scenario: Delete it
- **WHEN** the person says "delete this booking"
- **THEN** the layer picks nothing to carry out and the agent asks for the confirmation

### Requirement: Only the phrase and the option labels leave the process
A chooser outside the process SHALL receive only the person's phrase and the labels of the options. An option SHALL NOT hold a guest's name or phone; a request or a booking is an option by its number or its time. Every call to a paid chooser SHALL be counted in the run's stats.

#### Scenario: A booking picked by time
- **WHEN** the person says "open the eight o'clock booking" and the screen lists bookings with guests' names
- **THEN** the options sent hold the bookings' times and numbers and no name

### Requirement: The layer hands back instead of claiming
The layer SHALL say that something was opened or set only after the place was found and the form applied the value without complaint. When the place is not there, the value is refused by the form or the server, the person rejects it, or the chooser is not sure which field or value is meant, the turn SHALL go to the agent, and nothing SHALL be said to be done.

#### Scenario: A value the form refuses
- **WHEN** the layer picks a time slot and the form answers that the slot is taken
- **THEN** nothing is said to be set, and the agent explains and offers the nearest slot

#### Scenario: Two fields fit
- **WHEN** the person says "put 18" and both the hour and the number of guests could take it
- **THEN** nothing is written and the agent asks one question

### Requirement: An order with more in it keeps both parts
When a line holds an order the layer can carry out and something only the agent can do (a question, a text to write), the order SHALL be carried out and the rest SHALL go to the agent together with what was already done. When the person says right after an action that it was not what they meant, the action SHALL be undone and the agent SHALL ask what was meant.

#### Scenario: Open it and answer
- **WHEN** the person says "open the booking for three, what did they ask for?"
- **THEN** that booking opens and the agent answers the question about it

### Requirement: A date is not a place and a name off the screen is the agent's
A line that holds a date or a weekday SHALL NOT be carried out as a navigation: with a date field on the screen it is a value, otherwise the turn goes to the agent. A line that holds a person's or a company's name that no label on the screen has SHALL go to the agent and SHALL NOT be sent to a chooser. Both are decided in code.

#### Scenario: A weekday alone
- **WHEN** the person says "put Friday" on a screen with a date field
- **THEN** the calendar section is not opened, and the line is handled as a value for the date
