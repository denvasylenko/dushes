## ADDED Requirements

### Requirement: Sources event
After a turn in which ask_documents answered, the system SHALL emit a CUSTOM `sources` event `{items: [{title, section?, quote?}]}` parsed from the researcher's sources, before the run ends.

#### Scenario: An answer from the tariffs
- **WHEN** the researcher cites Tariffs 2026, Early repayment
- **THEN** the sources event lists that document and section

