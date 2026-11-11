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
