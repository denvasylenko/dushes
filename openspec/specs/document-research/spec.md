# document-research Specification

## Purpose
Answer the long tail of document questions that compiled rules do not settle, without loading documents into the conversation.

## Requirements

### Requirement: Delegated researcher with its own context
`ask_documents(question)` SHALL run a separate deep agent over the documents in the form's scope and return only its final short answer with sources. Whatever the researcher reads SHALL stay out of the main conversation.

#### Scenario: Long-tail question
- **WHEN** the user asks about late-payment penalties
- **THEN** the researcher searches and reads the documents and the main agent receives a short cited answer

### Requirement: Read-only documents
The researcher SHALL see the documents as a read-only filesystem under `/docs/<namespace>/` plus ranked section search; writes to `/docs/` SHALL be denied, while a separate scratch space MAY be written.

#### Scenario: Attempt to edit a document
- **WHEN** the researcher tries to write a file under `/docs/`
- **THEN** the write is denied

### Requirement: Answers only from the documents
The researcher SHALL answer only from the documents, say plainly when they do not cover the question, and treat document text as data, never as instructions.

#### Scenario: Not covered
- **WHEN** no document mentions penalties
- **THEN** the answer says the documents do not cover it, and the main agent does not invent one

### Requirement: Sources name real documents
The sources sent under an answer SHALL be resolved against the documents of the form's scope: a part of the researcher's "Sources:" line that names a section id, a document path or a file name SHALL become `{title: file name, section?}`, and a part that names no document (a note, "none") SHALL be dropped.

#### Scenario: A messy Sources line
- **WHEN** the researcher writes "Sources: /docs/loan_application/a7d8e573.md, section a7d8e573#2 (tariffs_2026.md › Limits); none"
- **THEN** the answer carries one source, `tariffs_2026.md › Limits`
