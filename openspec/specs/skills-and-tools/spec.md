# skills-and-tools Specification

## Purpose
Extend the agent per form with know-how (skills) and with server-side tools, without changing the core.

## Requirements

### Requirement: Skills with progressive disclosure
A skill SHALL have a name, a description, markdown instructions, the forms it applies to (`*` for all) and optional tools. Skills SHALL be loadable from folders with a `SKILL.md` (YAML frontmatter: name, description, forms, tools as import strings) or built in code. Only name and description SHALL be in the system prompt; `use_skill(name)` SHALL return the full instructions.

#### Scenario: Skill scoped to one form
- **WHEN** the `gift_cards` skill lists only `barber_booking`
- **THEN** the loan form's prompt and tools do not include it

### Requirement: Extra tools
Tools contributed by skills (for their forms) and tools configured for all forms SHALL be bound to the model and executed by the agent, with failures returned to the model as tool errors.

#### Scenario: Skill tool call
- **WHEN** the model calls `check_gift_card` with a valid code
- **THEN** the tool result with the balance is returned to the model
