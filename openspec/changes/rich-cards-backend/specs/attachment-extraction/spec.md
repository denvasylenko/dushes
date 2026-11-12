## ADDED Requirements

### Requirement: Privacy note on upload requests
When `attachments.privacy_note` is set, upload requests SHALL carry it as `privacy`.

#### Scenario: A note configured
- **WHEN** the config sets a privacy note
- **THEN** the upload card carries it

### Requirement: The last extraction is remembered
The system SHALL keep the last extraction of each thread (document title, attachment id, values with confidence) so that later proposals can name their source.

#### Scenario: A later proposal
- **WHEN** values from the extraction are proposed in the next round
- **THEN** the card carries the document source

