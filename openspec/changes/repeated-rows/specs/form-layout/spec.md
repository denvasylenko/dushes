## ADDED Requirements

### Requirement: A repeat container holds rows of the same fields
A container mapped to the role `repeat` SHALL hold a template of fields written once in the JSX; its rows SHALL be addressed `<container>.<row>.<field>` with zero-based rows, the row count SHALL come from `props[<container>].rows` and the row keys in the config, and adding a row SHALL NOT change the layout's jsx_hash.

#### Scenario: Two order lines
- **WHEN** the JSX has `<Repeat name="items">` with `product` and `qty`, and the config has two rows
- **THEN** the agent's context lists `items.0.product`, `items.0.qty`, `items.1.product` and `items.1.qty` under the list "items, rows 2"

### Requirement: Forms without rows are unchanged
A layout without a repeat container SHALL parse, render and fill exactly as before, and plain field names SHALL keep their meaning.

#### Scenario: An existing form
- **WHEN** a form with no repeat container is registered
- **THEN** its outline and its cards are the same as before this change

### Requirement: Only a declared repeat makes a row name
A dotted name `x.N.y` SHALL be read as row N of the repeat container `x` only when `x` is a declared repeat container; any other dotted name (a nested object such as `address.city`) SHALL stay a plain field name.

#### Scenario: A nested object
- **WHEN** a form has a field named `address.city` and no repeat container named `address`
- **THEN** `address.city` is an ordinary field
