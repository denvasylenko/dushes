# component-values Specification

## Purpose
Let the agent work with any component library: each field tag describes how its component stores a value and its options, the agent reads stored values into one internal format, and it writes card and prefill values back in the form's own format.

## Requirements

### Requirement: Field specs describe how a component stores its value
Each entry of `components.fields` SHALL accept either a role string or a field spec object. Supported keys:
- `role`;
- `value`, the stored shape of a choice or number;
- `option_keys` and `options_prop`, where the options are and how they look;
- `true` and `false`, the stored checkbox values;
- `format`, the date format;
- `codec`.

A role string SHALL mean a spec with that role and defaults. An unknown role or key SHALL fail configuration loading with an error naming the tag.

#### Scenario: A bare role keeps the old behaviour
- **WHEN** the configuration maps `Dropdown: select`
- **THEN** a `Dropdown` reads options from `props.options` and stores the option object

#### Scenario: Allowed shapes
- **WHEN** a field spec sets `value`
- **THEN** the accepted values depend on the role:
  - `option`, `id` or `name` for `select` and `radio`;
  - `options`, `ids` or `names` for `multiselect`;
  - `number` or `string` for `number`;
- **AND** `format` accepts `iso`, a `strftime` pattern or `epoch_ms`

#### Scenario: A misspelt key
- **WHEN** a field spec has `optons_prop: items`
- **THEN** loading the configuration fails with an error naming the tag and the unknown key

### Requirement: Form values are read leniently into one internal format
The agent SHALL read every stored value through the field's spec into one internal format per role. It SHALL accept any plausible stored shape. "Filled", "not in the current options", the change diff and learned dependencies SHALL use the value as read.

#### Scenario: A dropdown that stores only the id
- **WHEN** a field spec has `value: id`, the options are `[{value: "auto", label: "Car loan"}]` and the stored value is `"auto"`
- **THEN** the field is filled, its value is shown as "Car loan", and it is not reported as out of the options

#### Scenario: Any choice shape is understood
- **WHEN** a dropdown stores an option object, an option id or an option label
- **THEN** each is read as the same choice

#### Scenario: A toggle with letters
- **WHEN** a field spec is `{role: bool, true: "Y", false: "N"}` and the stored value is `"N"`
- **THEN** the field counts as unchecked

#### Scenario: A value that cannot be read
- **WHEN** a date field with `format: "%d.%m.%Y"` stores `"tomorrow"`
- **THEN** the field is treated as filled with an unreadable value, its raw text is shown to the model, and no exception is raised

### Requirement: Values are written in the form's own format
Every value the agent hands to the client SHALL be encoded with the field's spec, so it can go to the form backend unchanged. This covers a card's `changes[].value` and a prefill result's `values[].value`. `display` SHALL stay a human-readable text.

#### Scenario: Custom option keys and id storage
- **WHEN** a field spec is `{role: select, value: id, options_prop: items}` and `props.items` is `[{value: "auto", label: "Car loan"}]`
- **THEN** a card that sets the field to "Car loan" has `value = "auto"` and `display = "Car loan"`

#### Scenario: Option objects are written back as given
- **WHEN** a field spec has `value: option` and the chosen option is `{value: "auto", label: "Car loan", group: "secured"}`
- **THEN** the card value is that same object, extra keys included

#### Scenario: A day-first date component
- **WHEN** a field spec is `{role: date, format: "%d.%m.%Y"}` and the model proposes `1991-02-03`
- **THEN** the card value is `"03.02.1991"`

#### Scenario: Numbers
- **WHEN** a number field with the default spec is set to `250 000`
- **THEN** the card value is the JSON number `250000`, and with `value: string` it is `"250000"`

### Requirement: Option keys are detected when not configured
When `option_keys` is not set, the agent SHALL find the id and label keys of option objects among the common pairs `id/name`, `value/label`, `key/label`, `value/text`, `code/name`, `code/title`. It SHALL accept options given as a list of strings, where the string is both id and label, or as an object mapping ids to labels. Options whose keys cannot be found SHALL be reported in the value warnings, and their objects SHALL be shown to the model as they are.

#### Scenario: Options from a typical UI kit
- **WHEN** a dropdown's options are `[{value: "m", label: "Male"}, {value: "f", label: "Female"}]` and no `option_keys` are set
- **THEN** the model sees the options `m: Male` and `f: Female` and can choose "Female"

### Requirement: Radio and multiselect roles
`radio` SHALL behave like `select` for reading, validation and writing. `multiselect` SHALL hold a list of choices:
- it counts as filled when the list is not empty;
- it is out of the options when any item is not among the current options;
- a proposal SHALL accept a list or a comma-separated text of ids or labels;
- each item SHALL be validated, and items not among the options SHALL be refused with the available options.

#### Scenario: Choosing two items
- **WHEN** the model proposes `["SMS", "email"]` for a multiselect whose options are `sms: SMS`, `email: Email`, `post: Post` and whose spec has `value: ids`
- **THEN** the card value is `["sms", "email"]` and the display is "SMS, Email"

#### Scenario: One unknown item
- **WHEN** one of the proposed items is not among the options
- **THEN** the change is refused with the available options and no card is shown for it

### Requirement: Custom codecs
A field spec with `codec` SHALL use an instance of that class:
- `decode(raw, props)` reads a stored value into the internal format of the role;
- `encode(value, props)` writes an internal value back.

Either method MAY be absent, and then the role's default is used. If the codec raises, the value SHALL be treated as unreadable (when decoding) or the change refused with the error (when encoding), never crashing the turn.

#### Scenario: A phone component with its own format
- **WHEN** a codec's `encode` turns `"+79001234567"` into `{country: "+7", number: "9001234567"}`
- **THEN** the card value is that object

### Requirement: Value warnings for a sample config
Registering a form with a config SHALL return warnings, in addition to the layout warnings, for:
- each field whose stored value cannot be read with its spec;
- each field whose options' keys cannot be found;
- each field whose options prop is missing for a choice role.

Each warning SHALL name the field and suggest the field spec key to set.

#### Scenario: Wrong value shape
- **WHEN** a `Dropdown` with the default spec stores `"auto"`, the options are objects with `id` and `name`, and `"auto"` is not an id
- **THEN** the warning names the field and says the value matches no option

### Requirement: Default tags for radio groups and multi-selects
The default component map SHALL include `RadioGroup` (radio) and `MultiSelect` (multi-select), besides the existing default tags.

#### Scenario: A generated skeleton
- **WHEN** a JSX skeleton uses `<RadioGroup name="gender"/>` and `<MultiSelect name="channels"/>` without a `components` configuration
- **THEN** the layout reads them as a radio group and a multi-select, with no unknown-tag warning
