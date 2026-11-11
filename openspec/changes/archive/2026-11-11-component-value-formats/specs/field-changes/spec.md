## MODIFIED Requirements

### Requirement: Values are normalized
A proposed value SHALL be checked and written in the field's own format (see component-values):

| Field | A proposal accepts | Written as |
|---|---|---|
| dropdown, radio | an option id or label | per the field spec, `{id, name}` with the default spec |
| multiselect | a list, or comma-separated ids or labels, each validated | per the field spec |
| checkbox | booleans or common yes/no words in several languages | |
| date | `YYYY-MM-DD` or `DD.MM.YYYY` | in the field's date format, ISO by default |
| number | with spaces or commas | a JSON number by default |

Each card change SHALL also carry `display`, the value as human text.

#### Scenario: Day-first date format
- **WHEN** the model proposes `birth_date = 03.02.1991` for a date field with the default spec
- **THEN** the card value is `1991-02-03`

#### Scenario: Number with spaces
- **WHEN** the model proposes `loan_amount = 250 000` for a number field with the default spec
- **THEN** the card value is the JSON number `250000` and the display is `250000`

#### Scenario: A dropdown that stores the id
- **WHEN** the field spec has `value: id` and the model proposes the label "Car loan" of option `auto`
- **THEN** the card value is `"auto"` and the display is "Car loan"
