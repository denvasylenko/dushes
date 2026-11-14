## ADDED Requirements

### Requirement: A skeleton read from the DOM (idea)
A host without JSX MAY let the formguide plugin build the form's skeleton from the live DOM by `data-name` attributes, tabs, accordions and sections; the plugin SHALL register it as the form's layout and register again only when the skeleton changes.

#### Scenario: A Vue form
- **WHEN** a Vue page marks its fields with data-name and turns on the DOM adapter
- **THEN** the agent sees the form's structure without any hand-written JSX
