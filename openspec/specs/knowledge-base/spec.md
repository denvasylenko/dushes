# knowledge-base Specification

## Purpose
Let managers attach business documents (policies, tariffs, requirements) to forms, scoped so that each form's assistant sees only the documents meant for it, and compile them into guidance the assistant always has.

## Requirements

### Requirement: Documents live in namespaces
Documents SHALL be uploaded into a namespace (by default the form id). Supported types SHALL be `.md`, `.txt` and `.pdf` (text extracted); other types SHALL be rejected. Namespaces SHALL be validated so that a path cannot escape the storage root.

#### Scenario: Unsupported file
- **WHEN** a manager uploads `x.exe`
- **THEN** the upload fails with a 400 and a message listing supported types

### Requirement: Scopes decide what a form sees
Each form SHALL see the namespaces listed in its scope, or only its own namespace when it has no scope. Search and compilation SHALL use only the namespaces in scope.

#### Scenario: Shared documents
- **WHEN** the loan form's scope is `[loan_application, bank_common]`
- **THEN** its searches return sections from both, and never from `barber_booking`

### Requirement: Pluggable search index
Section search SHALL be provided by a configurable index: a built-in BM25 index (in memory, rebuilt from stored sections on start) or an adapter over any LangChain vector store, filtered by namespace either natively (configured filter builder) or by over-fetching and filtering.

#### Scenario: Deleting a document
- **WHEN** a document is deleted
- **THEN** its sections are removed from the index and no longer returned by search

### Requirement: Compile documents into the domain pack
On demand (the demo runs it after every upload or delete), the system SHALL make one model pass over all documents in the form's scope and the form's field catalog and store: a summary, rules with sources, filling hints, and notes attached to existing fields. Notes for fields that do not exist SHALL be dropped and reported.

#### Scenario: Compiled rule answers a question
- **WHEN** the documents say the minimum consumer loan is 30 000 ₽ and the user asks for the minimum
- **THEN** the agent answers from the compiled rules without calling the researcher
