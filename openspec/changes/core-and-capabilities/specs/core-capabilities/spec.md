## ADDED Requirements

### Requirement: A core that capabilities plug into
The library SHALL provide `Core(config)` owning the knowledge base, models, conversation memory, transcripts, attachments and transcription. The Site agent (`Dushes`) and the UI agent (`UIAgent`) SHALL take a `Core`; `Dushes` SHALL work without a UI agent.

#### Scenario: A knowledge-only site
- **WHEN** a host configures Know and Show only
- **THEN** Dushes answers from the site map and documents and no UI agent is built

### Requirement: Capabilities in config
`capabilities` in the config SHALL switch on Know (knowledge, the Researcher), Show (site map, navigation, highlight), Fill (the UI agent), Do (host actions) and Analyze (data tools with chart and table cards); a missing key SHALL be off.

#### Scenario: Turning on Fill
- **WHEN** `capabilities.fill` is present
- **THEN** Dushes hands form work to the UI agent on form pages

### Requirement: Names and deprecated aliases
`FormGuide` SHALL be renamed `UIAgent`; `FormGuide` and `SiteGuide` SHALL stay importable as deprecated aliases with a warning for two minor versions, and existing calls such as `Dushes(form_guide, site)` SHALL keep working.

#### Scenario: The cabinet upgrades
- **WHEN** the cabinet imports `FormGuide` and `SiteGuide` from 0.4
- **THEN** its code runs unchanged and Python warns about the new names

### Requirement: Host actions with Undo or a confirm card
A Do action SHALL either run at once with an Undo on its result (when it declares how to undo) or go through a confirm card (when it does not).

#### Scenario: An action without Undo
- **WHEN** the agent calls a host action that cannot be undone
- **THEN** the user sees a confirm card and the action runs only after the tap
