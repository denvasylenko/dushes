# Spec Delta

## Purpose
Offer one quiet suggestion when the user seems stuck (an empty required field, a form error, leaving an unfinished form) without ever interrupting them.

## ADDED Requirements

### Requirement: Moments from the page
A run with `forwardedProps.moment {kind, target?}` and no new user message SHALL be treated as a moment, with `kind` one of `idle_field`, `form_error` or `leaving`. The run SHALL emit at most one `suggestions` event with one item, or nothing, and SHALL NOT emit text, cards or tool calls.

#### Scenario: Stuck on a field
- **WHEN** the page reports `idle_field` for `employer_inn`
- **THEN** the run ends with one suggestion such as "What goes in Company tax ID?" and no message

### Requirement: Nothing is recorded until tapped
A moment and its chip SHALL NOT enter the model's history or the transcript; tapping the chip SHALL send its text as an ordinary user message.

#### Scenario: Ignored chip
- **WHEN** the user ignores the chip and writes something else
- **THEN** the model's history has no trace of the moment

### Requirement: The widget detects moments
`<agui-chat proactive>` SHALL report `idle_field` after `idle_seconds` (default 30) of focus on an empty required field, `form_error` when the form shows a new error, and `leaving` when the page directs to another path with a draft open; it SHALL NOT report while the user types in the chat or a turn runs.

#### Scenario: Typing in the chat
- **WHEN** the user is typing a message while a field has been empty for 40 seconds
- **THEN** no moment is reported

### Requirement: Quiet limits
`proactive: {enabled, idle_seconds, max_per_page, kinds}` SHALL be off by default; at most `max_per_page` chips (default 1) SHALL be shown per page, and a dismissed chip's target SHALL NOT get another chip in that conversation.

#### Scenario: Off by default
- **WHEN** the config has no `proactive` section and the page reports a moment
- **THEN** the run emits nothing
