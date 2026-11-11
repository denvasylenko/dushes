# ui-guidance Specification

## Purpose
Show the user where to click: the agent names an element, and the frontend opens the tabs and accordions on the way to it and highlights it.

## Requirements

### Requirement: Focus directive with a reveal chain
`focus_field(name, hint)` SHALL emit a `ui_directive` with the target, a hint, and a reveal chain computed from the layout (each ancestor tab with its tabs group, each ancestor accordion), so the model never has to know the path.

#### Scenario: Field in a nested accordion
- **WHEN** the agent focuses `loan_type`
- **THEN** the directive's reveal chain is `[tab main/tab_loan, accordion acc_loan_params]`

### Requirement: Hidden targets are refused
Focusing a hidden element SHALL fail with an explanation, including a learned reason when one is known. Focusing a disabled element SHALL succeed and tell the model it is not editable yet.

#### Scenario: Hidden collateral field
- **WHEN** the agent tries to focus a field inside a hidden tab
- **THEN** the tool returns an error naming the hidden container
