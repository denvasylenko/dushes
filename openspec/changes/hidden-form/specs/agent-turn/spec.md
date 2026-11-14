## ADDED Requirements

### Requirement: A form the person does not see
When a run's state carries `ui.form_visible: false`, the agent SHALL be told the person does not see the form, SHALL NOT be offered `focus_field`, and SHALL NOT refer to a field's place, a tab or a button on the page; it SHALL collect and confirm values with cards and read them back in the chat.

#### Scenario: A chat-only form without a host hint
- **WHEN** a host runs a form with `ui.form_visible: false` and no flow hint about it
- **THEN** the agent fills it through cards and never tells the person to look at the form
