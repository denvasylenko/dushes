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
