# Spec Delta

## Purpose
Show a short checklist of what a long turn is doing, ticked as the turn advances, so the user sees progress instead of a spinner.

## ADDED Requirements

### Requirement: A plan for long turns
The form agent and Dushes SHALL have `show_plan(steps)` with two to five labels. When the model calls it, the run SHALL emit CUSTOM `plan {plan_id, steps: [{label, state: "pending"}]}` with the first step `"active"`. A second call in the same turn SHALL be ignored.

#### Scenario: A document question with a hand-off
- **WHEN** the model calls show_plan with "Reading the tariffs", "Comparing your options", "Opening the form"
- **THEN** the client gets a `plan` event with those three steps, the first active

### Requirement: The plan advances
After each finished tool round the run SHALL emit `plan` with the next step active and the previous done; when the answer's text starts every step SHALL be done; when the turn fails the active step SHALL be `"failed"`.

#### Scenario: The answer starts
- **WHEN** the model starts its answer after two tool rounds of a three-step plan
- **THEN** the last `plan` event shows all three steps done

### Requirement: The chat shows it
`<agui-chat>` SHALL show the latest plan as a checklist instead of the waiting dots, and SHALL keep it, all done, above the answer once the turn ends; a restored conversation SHALL show it the same way.

#### Scenario: After a reload
- **WHEN** the page reloads after a turn with a plan
- **THEN** the chat shows that plan, all done, above the answer

### Requirement: Short turns have no plan
The prompt SHALL tell the model to plan only turns of three or more steps; a turn without `show_plan` SHALL look as it does today.

#### Scenario: A simple question
- **WHEN** the user asks a question answered from the context with no tools
- **THEN** no `plan` event is emitted
