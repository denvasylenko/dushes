# ui-guidance Specification

## Purpose
Show the user where to click: the agent names an element, and the frontend opens the tabs and accordions on the way to it and highlights it.

## Requirements

### Requirement: Focus directive with a reveal chain
`focus_field(name, hint)` SHALL emit a `ui_directive` with the target, a hint, and a reveal chain computed from the layout (each ancestor tab with its tabs group, each ancestor accordion), so the model never has to know the path.

#### Scenario: Field in a nested accordion
- **WHEN** the agent focuses `loan_type`
- **THEN** the directive's reveal chain is `[tab main/tab_loan, accordion acc_loan_params]`

### Requirement: Several fields shown together
`focus_field` SHALL accept `fields`: more fields to highlight with the target. The directive SHALL carry them as `also`, keeping only the fields that are visible once the target's reveal chain is open; the tool result SHALL name the ones it skipped. The page SHALL ring every field in `also` together with the target, and scroll only to the target. Asked to "show" several fields, the agent SHALL show them in the form, not only list them in the chat.

#### Scenario: Show me the required fields
- **WHEN** the user writes "show me required fields in form" and the Spouse section has four empty required fields
- **THEN** the agent focuses the Spouse section with those four fields, the page rings all of them, and the reply says what comes next

#### Scenario: A field in another section
- **WHEN** `fields` names a field of another tab
- **THEN** it is left out of `also` and the tool result says it was not highlighted

### Requirement: Hidden targets are refused
Focusing a hidden element SHALL fail with an explanation, including a learned reason when one is known. Focusing a disabled element SHALL succeed and tell the model it is not editable yet.

#### Scenario: Hidden collateral field
- **WHEN** the agent tries to focus a field inside a hidden tab
- **THEN** the tool returns an error naming the hidden container
