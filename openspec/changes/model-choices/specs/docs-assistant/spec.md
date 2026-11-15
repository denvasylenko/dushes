## ADDED Requirements

### Requirement: The docs assistant's model choices
The docs assistant SHALL accept the host's model choices by name, one per question, and MAY change the choice within a conversation; an unknown name SHALL be refused. It SHALL send the same `CUSTOM model` event.

#### Scenario: The same question on two models
- **WHEN** a visitor asks a question on haiku and then asks it again on luna in the same conversation
- **THEN** each answer comes from the named model and carries its `model` event

### Requirement: Demo budgets per model
The demo host SHALL price every run by the model of each of its calls, SHALL keep a daily budget per choice and in total, and SHALL list at `GET /agent/models` each choice with whether it is usable and has budget left.

#### Scenario: Prices by model
- **WHEN** a run's calls were made by two models
- **THEN** each call is priced by its own model's row of the price file

### Requirement: Falling back when one budget is used up
When the run's choice has no budget left and the total has, a new conversation SHALL be answered by the other choice with a `CUSTOM notice` saying so, and a run of an existing conversation SHALL be refused with HTTP 429, `reason: "model_cost"` and the other choice's name. When the total is used up every run SHALL be refused as before.

#### Scenario: Luna's budget is gone
- **WHEN** luna has used its 2 dollars, the total stands at 3.50 of 5, and a visitor starts a conversation on luna
- **THEN** haiku answers, and the chat shows that Luna's budget for today is used up
