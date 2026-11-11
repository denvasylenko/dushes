## ADDED Requirements

### Requirement: Questions that fill their field
When `ask_user` names a `field` that is a dropdown, radio group or multi-select and is editable now, the question card SHALL carry:
- `applies: true`;
- for each option, its `value` in the form's own format;
- `previous` and `previous_display`, the field's value before the answer.

#### Scenario: Options in the form's format
- **WHEN** the field's component stores only the option id
- **THEN** each option's `value` is its id

### Requirement: An applied answer counts as filling the field
A resume with `{answer: {ids}, config}` SHALL count as the user filling the question's field. The model SHALL be told the field was filled with the chosen option, with the form's reaction (the diff), and SHALL be told not to propose that field again.

#### Scenario: A loan type in one tap
- **WHEN** the model asks "What type of loan do you need?" with `field: loan_type`, and the client applies "Car loan" and resumes with the new config
- **THEN** the model's tool result says `loan_type` was filled with Car loan (auto), followed by the form's changes, and no field-change card follows

### Requirement: Questions that only answer
A question SHALL keep today's behaviour, where the answer is returned and the model proposes the value in a card, when:
- the question has no `field`;
- its field is locked, hidden or read-only;
- the answer is typed text;
- the resume carries no `config`.

#### Scenario: A client that does not apply
- **WHEN** a client resumes a question that has `applies: true` with only `{answer: {ids: ["auto"]}}`
- **THEN** the model receives "The user chose: Car loan (auto)", and the field stays as it was
