## ADDED Requirements

### Requirement: The model can ask for a confirmation
The agent SHALL offer a tool `confirm_action` with `title`, `message`, an optional `confirm_label` and `danger` (default false). A call SHALL pause the turn with an interrupt of `type: "confirm"` and `{card_id, title, message, confirm_label, danger}`. The resume `{accepted}` SHALL be returned to the model as "The user confirmed." or "The user declined."; a cancelled resume counts as declined. Its structured reason SHALL be `confirm_action`.

#### Scenario: Before submitting
- **WHEN** a skill tool would submit the application and the model calls `confirm_action` with "Submit the application?"
- **THEN** the user sees a confirmation card, and the model learns the decision before it calls the submit tool

### Requirement: Confirmation required by configuration
`confirm_tools` in the configuration SHALL list tool names that always need a confirmation. A call to such a tool SHALL be held, the user SHALL be shown a confirm card naming the tool and its arguments, and the tool SHALL run only if the user accepts. Otherwise the model SHALL get "The user declined; the tool was not run."

#### Scenario: A guarded tool
- **WHEN** `confirm_tools: [submit_application]` is set and the model calls `submit_application`
- **THEN** the tool runs only after the user accepts the confirm card
