## MODIFIED Requirements

### Requirement: Configurable component library
The mapping from JSX tags to roles SHALL be configurable.
- Container roles: tabs, tab, accordion, section, form.
- Field roles: text, number, date, select, radio, multiselect, bool, file.

A field tag SHALL map to a role string or to a field spec that also describes how the component stores its value (see component-values). Unknown tags SHALL be kept with role `unknown` and reported as a warning instead of failing.

#### Scenario: A custom component library
- **WHEN** the configuration maps `Wizard` to `tabs`, `Step` to `tab` and `TextField` to `text`
- **THEN** a JSX of those tags is parsed without warnings and `Step` nodes are containers

#### Scenario: A field spec instead of a role
- **WHEN** the configuration maps `Select` to `{role: select, value: id, options_prop: items}`
- **THEN** `Select` nodes are fields with the role `select`, and their values and options are read with that spec

#### Scenario: Problems in the JSX
- **WHEN** the JSX has an unknown tag, a duplicate `name`, an unbalanced or unclosed tag, or a node without `name`
- **THEN** the layout is still built, a stable generated name is used where needed, and a warning describes each problem
