## ADDED Requirements

### Requirement: Requested uploads
The agent SHALL offer a tool `request_file` with `prompt`, `accept` (limited to the supported file types), `multiple` and an optional `field`. A call SHALL pause the turn with an interrupt of `type: "upload"`.

#### Scenario: The upload card
- **WHEN** the model calls `request_file` with the prompt "Upload your passport" and `accept: ".pdf,.jpg"`
- **THEN** the client receives an `upload` interrupt with that prompt and those types

### Requirement: Answering an upload request
The resume SHALL carry `{attachment_ids}`, the ids that `POST /attachments` returned for this thread. The model SHALL receive the file names and ids so it can call `extract_from_attachment`. Unknown ids SHALL be dropped. A resume with no ids, or a cancelled one, counts as skipped.

#### Scenario: Asking for a passport scan
- **WHEN** the user uploads `passport.pdf`
- **THEN** the model's tool result names `passport.pdf` with its attachment id, and the model reads it with `extract_from_attachment`
