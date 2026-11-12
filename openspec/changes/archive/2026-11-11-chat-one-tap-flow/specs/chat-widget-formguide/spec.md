## ADDED Requirements

### Requirement: Deferred rows on the card
A deferred row SHALL show its label, the proposed option and a muted "after <field>". Accepting SHALL apply the other kept rows, then look up the deferred row's option in the refreshed form and apply it. A row whose option is not found SHALL show "not available" and SHALL be left out of `names`.

#### Scenario: Make and model in one tap
- **WHEN** the user accepts a card with Make = Toyota and a deferred Model = Camry
- **THEN** the widget applies Make, then Model with the Camry option from the refreshed list, and resumes once

### Requirement: Folded cards
After a field-change card is accepted or rejected, its rows SHALL fold into the result line ("✓ Filled in · Make, Year", with Undo while it lasts). Clicking the line SHALL show or hide the rows.

#### Scenario: A short thread
- **WHEN** the user accepts a card with three rows
- **THEN** the card shows one line with the three labels, and the rows appear on click

### Requirement: Readable values on cards
Number values on cards SHALL be formatted for the chat's language (1500000 -> "1,500,000" in English). A reason equal to the value SHALL be hidden. Question text SHALL render inline markdown (bold, italics, code).

#### Scenario: An amount
- **WHEN** a card proposes `loan_amount` 900000 instead of 1500000 in English
- **THEN** it shows "~~1,500,000~~ 900,000"
