# attachment-extraction Specification

## Purpose
Let users attach documents (scans, photos, PDFs, text) and have field values extracted from them, without the document entering the main conversation.

## Requirements

### Requirement: Attachments are scoped to a conversation
Attachments SHALL be stored per thread, limited in size (default 10 MB) and type (PDF, PNG, JPEG, WebP, GIF, TXT, MD), and SHALL be loadable only by id within the same thread.

#### Scenario: Another thread
- **WHEN** a conversation asks for an attachment id uploaded in a different thread
- **THEN** the attachment is not found

### Requirement: Separate extraction call
`extract_from_attachment(attachment_id, fields?, container?)` SHALL send the document and a catalog of candidate fields (name, label, path, type, options) to a separate model call with structured output, and return to the main agent only the values found, each with confidence, evidence and whether the field is editable now. Read-only and file fields SHALL not be candidates.

#### Scenario: Employment letter
- **WHEN** the user attaches an employment letter and the employer block is hidden until the employment type is chosen
- **THEN** the agent first proposes the employment type, then the employer fields with values from the letter

### Requirement: Values for locked steps are kept
Values for fields that are disabled now SHALL be marked "disabled now (fill later)" so the agent can propose them once the step unlocks.

#### Scenario: Business card on a locked step
- **WHEN** a business card is attached while the contact step is locked
- **THEN** the agent does not propose the contact fields yet and tells the user it will fill them once the step unlocks

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

### Requirement: Large photos are shrunk for the model
Before an image goes to a model, an image larger than 2000 px on a side or 3.5 MB SHALL be scaled down to at most 2000 px and re-encoded (JPEG, or PNG when it has transparency) under 3.5 MB, so it fits the model's per-image limit. Smaller images SHALL be sent unchanged.

#### Scenario: A 10 MB phone photo
- **WHEN** the user uploads a 10 MB PNG photo of a passport and the agent reads it
- **THEN** the model receives a JPEG of at most 2000 px and 3.5 MB, and the extraction does not fail on the size

