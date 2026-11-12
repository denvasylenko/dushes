## ADDED Requirements

### Requirement: Schema bridge
`schemaForm(schema, access)` SHALL build, from a declarative form schema and the form library's getters and setter:
- the JSX skeleton with the default tags;
- a config whose props come from the schema, with rules given as functions of the current values;
- an `apply(changes)` that writes accepted values through the setter and returns the rebuilt config.

#### Scenario: A dependent dropdown
- **WHEN** the schema gives `car_model` options as a function of `car_make`, and `car_make` is set to Toyota
- **THEN** the next config lists Toyota's models in `props.car_model.options`

### Requirement: Value conversion
Choice values SHALL be stored in the form's own format, `valueAs` (`id` by default, or `option`, `name`). In the config they SHALL be option objects `{id, name}`; values applied from cards SHALL be converted back before the setter is called.

#### Scenario: Ids in the form
- **WHEN** a card applies `loan_type: {id: "auto", name: "Car loan"}` to a field with the default `valueAs`
- **THEN** the setter receives `"auto"`

### Requirement: react-hook-form hook
`useFormguide(form, schema, options)` SHALL register the layout once, expose `ready`, `error` and `plugins` for `<AguiChat>`, read errors from `formState.errors`, apply values with `setValue`, and handle "show me" by calling `onReveal(section)` and then scrolling to and focusing the field found by `data-name` or `name`.

#### Scenario: Errors reach the agent
- **WHEN** react-hook-form has an error "Must be 10 digits" on `phone`
- **THEN** the config sent with the next run has `props.phone.error` equal to that message
