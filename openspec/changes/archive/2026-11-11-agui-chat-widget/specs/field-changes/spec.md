## ADDED Requirements

### Requirement: Previous values on cards
Each card change SHALL carry `previous` and `previous_display`: the field's value before the change, in the form's own format and as human text. Both SHALL be null when the field was empty.

#### Scenario: Changing a filled field
- **WHEN** the agent proposes `first_name = Anna` while the field holds `Ana`
- **THEN** the change has `previous: "Ana"`, `previous_display: "Ana"` and `display: "Anna"`

### Requirement: Values edited on the card
A field-change resume MAY carry `edited: {name: value}` for values the user changed on the card before accepting. The frontend SHALL apply the edited values instead of the proposed ones. The model SHALL be told which values the user edited, and the form's reaction SHALL be judged from the new config as usual.

#### Scenario: The user corrects an amount
- **WHEN** the resume has `edited: {loan_amount: 1200000}`
- **THEN** the model's tool result says the user changed `loan_amount` to 1200000 before applying it
