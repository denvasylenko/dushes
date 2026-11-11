# form-state Specification

## Purpose
Apply the latest config (flat `props` and `state` keyed by component name) on top of the static layout, compare it with the previous config, and learn field dependencies that the config does not declare.

## Requirements

### Requirement: Effective flags are inherited
A node SHALL be effectively hidden if it or any ancestor is not visible, and effectively disabled if it or any ancestor is disabled. A field that exists in the JSX but has no props in the config SHALL be treated as not rendered.

#### Scenario: Field inside a disabled tab
- **WHEN** a tab's props have `disabled: true` and a field inside it has `disabled: false`
- **THEN** the field is effectively disabled and cannot be filled by the agent

### Requirement: Progress counts only fillable fields
Progress for a container SHALL count required fields that are visible, enabled and not read-only, and SHALL treat a checkbox as filled only when it is checked.

#### Scenario: Required field in a locked step
- **WHEN** a required field is inside a disabled container
- **THEN** it is not counted in that container's progress, and the container reports how many required fields it holds

### Requirement: Semantic diff between messages
The system SHALL compare the current config with the snapshot taken at the previous message and report: value changes (split into user, agent-confirmed and form-derived), sections that appeared or were hidden, fields that became available or disabled, required changes, options changes, new and fixed errors, and selected values that are no longer in the options. A change that its parent container already explains SHALL be reported once, at the container.

#### Scenario: Choosing a value reveals a tab
- **WHEN** the user changes `loan_type` and the config now shows the Collateral tab
- **THEN** the diff lists the user change and `+ appeared tab_collateral`, without listing every field inside the tab

#### Scenario: Options change invalidates a value
- **WHEN** the region changes and the selected city is no longer among the city options
- **THEN** the diff reports that the selected city value is no longer in the options

### Requirement: Dependencies learned from observation
The system SHALL record which field changes are followed by which effects on other nodes, keyed by trigger value, and persist the map per form layout. A dependency SHALL be shown as a hint only after an exact observation (exactly one field changed) or enough accumulated weight across sessions. When several fields changed, dropdowns and checkboxes SHALL be preferred as causes over free text.

#### Scenario: A batch of edits
- **WHEN** two fields changed between messages and a tab appeared
- **THEN** no confident hint is shown for that tab

#### Scenario: A single edit
- **WHEN** only `loan_type` changed and the Collateral tab appeared
- **THEN** later contexts may say the tab "usually appears when loan_type = Mortgage (seen 1x)"
