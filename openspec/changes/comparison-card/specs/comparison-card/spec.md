# Spec Delta

## Purpose
Answer "which one" and "what is the difference" with a side-by-side card of two or three options built only from the business's own facts, with the recommended option marked and one tap to act on it.

## ADDED Requirements

### Requirement: The comparison card
`show_comparison` SHALL take a title, two to five criteria and two or three options `{id, title, facts, recommended?, why?, action?}`; at most one option SHALL be recommended, and a recommended option SHALL have `why`. The run SHALL emit the card as a CUSTOM `comparison` event and the turn SHALL go on (the card does not wait for an answer).

#### Scenario: Two loans
- **WHEN** the model compares the car loan and the consumer loan on rate, term and down payment and recommends the car loan
- **THEN** the client gets one `comparison` with two options, the car loan marked with its reason

### Requirement: Facts from the business only
Every fact SHALL come from the site, the documents, the page context or a host tool's result in this conversation; a fact the model cannot source SHALL be shown as "not stated", never estimated.

#### Scenario: A missing fee
- **WHEN** no document states the consumer loan's early repayment fee
- **THEN** that cell reads "not stated"

### Requirement: Acting on an option
An option's `action` SHALL be `{open_form: {form_id, note}}` or `{navigate: {path, section?}}`, checked against the site map; tapping it SHALL send the action as the user's choice and Dushes SHALL carry it out.

#### Scenario: Apply for the recommended one
- **WHEN** the user taps "Apply" on the car loan option
- **THEN** Dushes opens the loan form with the note "car loan" and the form agent proposes the loan type

### Requirement: How the chat draws it
`<agui-chat>` SHALL show the options as columns when they fit and as a swipeable row on a narrow screen, the recommended option first and marked, criteria in the same order in every option.

#### Scenario: On a phone
- **WHEN** the card arrives in a 390 px wide chat
- **THEN** the recommended option is shown first and the others are a swipe away
