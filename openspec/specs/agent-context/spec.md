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

### Requirement: The form agent reads its page
When a run's form state carries `page` (`{title, description, sections: [{title, text}]}`), every message to the form agent SHALL include it as a `<page_facts>` block, cut to 4000 characters, and the agent SHALL answer from it and SHALL NOT say the form or the page lacks a fact it holds or add detail the page does not state; the block is data, never instructions. Dushes SHALL fill `page` from the site map for the page the form sits on, unless the host gave one.

#### Scenario: A fee stated on the page
- **WHEN** the page of a registration form says "Registration costs 27.90 EUR" and the user asks the form agent what it costs
- **THEN** the agent answers 27.90 EUR and does not say the form shows no fee

### Requirement: The context says whether the form was sent
The form context SHALL say what the form reports about being sent, read from `submitted` in the props of the form's root component: a true value or `{reference, at}` gives a line that the form has been sent, with those details; `false` gives a line that it has not been sent yet; without the key no such line is added.

#### Scenario: The form reports a reference
- **WHEN** the root's props carry `submitted: {reference: "A-118"}` and the user asks whether it was sent
- **THEN** the agent says it was sent and gives the reference A-118

### Requirement: The context says who sends the form
When the run has no tool that acts and the form does not report that it was sent, the form context SHALL say that the person sends the form with the form's own send button, that nothing is sent from the chat, and that the agent never says it was sent and never answers that it cannot tell. For a form the person does not see (`ui.form_visible: false`) it SHALL say instead that the chat cannot send it, and name no button, portal or step.

#### Scenario: Asked whether it went through
- **WHEN** a form without a sending tool is filled in and the user asks "was it sent?"
- **THEN** the agent answers that it is sent from the form, not from the chat, and names what is missing or says it is ready to send
