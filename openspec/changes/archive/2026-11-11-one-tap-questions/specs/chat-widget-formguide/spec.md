## ADDED Requirements

### Requirement: One-tap answers
For a question card with `applies: true`, choosing an option SHALL do the following:
- call `applyChanges({field: value})` with the option's value, or with the list of values for a multiple choice;
- resume with `{answer: {ids}, config, ui}`;
- shrink the card to "✓ <label>" with Undo.

If `applyChanges` fails, the card SHALL stay open with the error. Undo SHALL put the previous value back and tell the agent.

#### Scenario: Choosing a loan type
- **WHEN** the user taps "Car loan" on a question card that applies to `loan_type`
- **THEN** `applyChanges` gets `{loan_type: <the option's value>}`, the run resumes with the new config, and the card shows "✓ Car loan" with Undo

### Requirement: Fill-in labels count the fields
A field-change card's main button SHALL say how many fields it fills, with the language's plural form: "Fill in 1 field", "Fill in 3 fields". When some rows are unticked, it SHALL say "Fill in 2 of 3".

#### Scenario: A card with one change
- **WHEN** a card proposes one field
- **THEN** its button reads "Fill in 1 field"
