## ADDED Requirements

### Requirement: Guides have one shape
Every guide page SHALL say in one plain sentence what it is and when it is needed, show a picture or diagram, give a minimal example, explain that example line by line with each public name linked to its reference row, say what the reader will see, and list common mistakes by their symptom. A term of the protocol or the code SHALL appear in a guide's prose only as a link to its explanation.

#### Scenario: A reader opens a guide for the first time
- **WHEN** a developer who has never used Dushes opens a guide
- **THEN** the first screen tells them what the page is for, and every name in its example leads to a row that explains it

### Requirement: A complete reference
Every public hook, component, function, option, method, event and configuration key SHALL have a reference row with its type, its default and one sentence on what it is for, and the build SHALL fail when a public name has no row.

#### Scenario: A new option
- **WHEN** an option is added to the form plugin without a reference row
- **THEN** the docs build fails and names the option

### Requirement: The docs are measured by a reader with no context
The project SHALL keep a set of developer tasks with answer keys and SHALL run them with a reader that sees only the built site; a docs change of this size is done when at least nine of ten tasks pass with no hints.

#### Scenario: A rewrite is finished
- **WHEN** the guides have been rewritten
- **THEN** the benchmark is run again and its before and after numbers are reported
