## ADDED Requirements

### Requirement: Commands are declared in the config
A host SHALL declare commands in one place, `commands:` in the configuration (or in Python), each with a unique `name`, a `description`, optional `args` and exactly one of `run.tool`, `run.page`, `run.prompt` or `run.skill`; a command MAY be scoped to forms or page paths. An invalid command SHALL fail the configuration with a message naming it.

#### Scenario: A command with two run kinds
- **WHEN** a command has both `run.tool` and `run.page`
- **THEN** loading the configuration fails and names the command

### Requirement: The widget learns the commands from the server
The restore response and every run's state snapshot SHALL carry `commands: [{name, description, args, icon?}]` for the current form or page, without `run`. The widget's own option SHALL merge with the list by name, and keyboard shortcuts SHALL come only from it.

#### Scenario: A page with scoped commands
- **WHEN** the user is on `/loans/car` and one command is scoped to `/loans/*`
- **THEN** the restored thread lists that command, and after the visitor moves to a page outside `/loans/` the next state snapshot does not

### Requirement: Running a command
A run with `forwardedProps.command_call = {name, args}` SHALL be validated against the configured commands; a `prompt` command SHALL run as the user's message, a `page` command SHALL navigate, and a `tool` or `skill` command SHALL run under the same confirmation and Undo rules as when the agent calls it. An unknown command or invalid args SHALL get a short answer and no tool call.

#### Scenario: A tool command that needs confirmation
- **WHEN** the user runs a command whose tool is in `confirm_tools`
- **THEN** a confirmation card comes first and the tool runs only after the user accepts
