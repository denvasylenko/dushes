# action-confirmations Specification

## Purpose
Let the agent ask the user for an explicit yes or no before an action with side effects, and let the configuration require that confirmation for named tools, so nothing irreversible happens without the user's consent.

## Requirements

### Requirement: The model can ask for a confirmation
The agent SHALL offer a tool `confirm_action` with `title`, `message`, an optional `confirm_label` and `danger` (default false). A call SHALL pause the turn with an interrupt of `type: "confirm"` and `{card_id, title, message, confirm_label, danger}`. The resume `{accepted}` SHALL be returned to the model as "The user confirmed." or "The user declined."; a cancelled resume counts as declined. Its structured reason SHALL be `confirm_action`.

#### Scenario: Before submitting
- **WHEN** a skill tool would submit the application and the model calls `confirm_action` with "Submit the application?"
- **THEN** the user sees a confirmation card, and the model learns the decision before it calls the submit tool

### Requirement: Confirmation required by configuration
`confirm_tools` in the configuration SHALL list tool names that always need a confirmation. A call to such a tool SHALL be held, the user SHALL be shown a confirm card naming the tool and its arguments, and the tool SHALL run only if the user accepts. Otherwise the model SHALL get "The user declined; the tool was not run." Either way the held call's result SHALL reach the client as a `TOOL_CALL_RESULT` for that call.

#### Scenario: A guarded tool
- **WHEN** `confirm_tools: [submit_application]` is set and the model calls `submit_application`
- **THEN** the tool runs only after the user accepts the confirm card

### Requirement: One confirmation, and it is the system's
For a tool listed in `confirm_tools` the only confirmation SHALL be the held tool's own card: the tool's description SHALL say it asks the user itself, and a `confirm_action` call while such a tool is available SHALL be refused with a message naming the tool, unless the call says `other_action: true` (an action none of these tools performs). The agent SHALL NOT ask for the confirmation in text.

#### Scenario: Sending a change
- **WHEN** a host lists `submit_deputy_change` in `confirm_tools` and the user asks to send the change
- **THEN** exactly one confirmation card is shown, the held tool's, and the tool runs only after the user accepts it

### Requirement: Nothing to confirm without a tool that acts
When a run has no host tool, no skill tool and no page (client) tool, the agent SHALL NOT be offered `confirm_action`, and `review_form` in `submit` mode SHALL show the `status` card, which has no send button. A review answered with `submit` SHALL then tell the model it has no tool that sends the form.

#### Scenario: A form the person sends themselves
- **WHEN** a form has no tool that sends it and the user says "send it"
- **THEN** no confirmation card is shown, and the agent says what is still missing or that the form is ready and is sent with the form's own send button
