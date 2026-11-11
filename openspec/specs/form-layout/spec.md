# form-layout Specification

## Purpose
Turn the form's JSX string, which carries only tags, a `name` attribute and occasional text, into a static structure the agent can navigate: containers, fields, nesting and on-screen order.

## Requirements

### Requirement: Parse the JSX once per layout
The system SHALL parse a JSX string into a layout index of nodes (tag, role, name, parent, children, text) and SHALL cache it by a hash of the JSX, so that the same form is parsed once for all users.

#### Scenario: Registering the same JSX twice
- **WHEN** a form is registered with a JSX string that was registered before
- **THEN** the cached layout is reused and the same `jsx_hash` is returned

#### Scenario: Static text inside a container
- **WHEN** a container in the JSX contains plain text
- **THEN** the text is kept as a static-text node in its parent, in document order

### Requirement: Addresses encode nesting and order
Every node SHALL get an address of dot-separated positions (for example `1.2.3`) that encodes both its nesting and its order among siblings in the JSX.

#### Scenario: A field three levels deep
- **WHEN** a field is the 2nd child of the 2nd container inside the 1st tab
- **THEN** its address is `1.1.2.2`

### Requirement: Configurable component library
The mapping from JSX tags to roles SHALL be configurable (container roles: tabs, tab, accordion, section, form; field roles: text, number, date, select, bool, file). Unknown tags SHALL be kept with role `unknown` and reported as a warning instead of failing.

#### Scenario: A custom component library
- **WHEN** the configuration maps `Wizard` to `tabs`, `Step` to `tab` and `TextField` to `text`
- **THEN** a JSX of those tags is parsed without warnings and `Step` nodes are containers

#### Scenario: Problems in the JSX
- **WHEN** the JSX has an unknown tag, a duplicate `name`, an unbalanced or unclosed tag, or a node without `name`
- **THEN** the layout is still built, a stable generated name is used where needed, and a warning describes each problem
