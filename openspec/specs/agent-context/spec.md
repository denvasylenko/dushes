# agent-context Specification

## Purpose
Give the model a small, current picture of the form on every message instead of the raw config: a collapsed outline, the section the user has open, and what changed.

## Requirements

### Requirement: Per-message form context
Every user message SHALL be sent to the model together with a form context containing the user's local time, a form outline with progress, the focused section, and the changes since the previous message, followed by an instruction to reply in the language of the user's message.

#### Scenario: First message
- **WHEN** a conversation starts
- **THEN** the context contains NOW, FORM, FOCUS and "CHANGES: this is the first message"

### Requirement: Outline stays small for large forms
The outline SHALL expand only the top levels and the containers on the user's screen, collapse other branches with a count, and show hidden containers as one line with a known reason when available. Field details SHALL appear only for the focused section; other details SHALL be available through tools.

#### Scenario: A 221-field form
- **WHEN** the loan demo form is rendered at its initial state
- **THEN** the outline and focus together are at least five times smaller than the serialized config

### Requirement: Focus follows the user's screen
The focused section SHALL be the container of the field under the cursor if it is on screen, otherwise the last opened accordion on screen, otherwise the deepest open container.

#### Scenario: Cursor in a field
- **WHEN** the UI state says the cursor is in `children_count`
- **THEN** FOCUS shows the section containing that field and names the field

### Requirement: Personal data is masked
Values of fields listed as PII in the domain pack SHALL be shown to the model as `<filled>`.

#### Scenario: Passport number in the config
- **WHEN** `passport_number` is PII and has a value in the config
- **THEN** the value does not appear in any context or tool result

### Requirement: Disabled sections explain themselves
For a disabled section the context SHALL give a learned reason when one is reliable; otherwise it SHALL mark the reason as unknown and offer a GUESS listing required empty fields earlier in the form, grouped by step with the nearest step first.

#### Scenario: Locked Collateral tab
- **WHEN** the Collateral tab is disabled and no dependency is known
- **THEN** the reason starts with "cause unknown; GUESS" and the first group is the Loan tab
