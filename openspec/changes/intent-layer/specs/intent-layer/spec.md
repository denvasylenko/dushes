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
