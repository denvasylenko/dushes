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

### Requirement: Sections of large documents
A document SHALL be cut into sections on its headings and then on paragraphs to about `knowledge.chunk_chars`, with `knowledge.chunk_overlap` characters shared by neighbours; a table or a list SHALL stay whole while it fits twice that size. Each section SHALL keep its heading path, its page for a PDF and its order in the document.

#### Scenario: A clause deep in a handbook
- **WHEN** a 300-page PDF has "4.2 Late payment" under "4 Fees" on page 118
- **THEN** its section carries the path "4 Fees > 4.2 Late payment" and page 118

### Requirement: A prebuilt index
The built-in search SHALL use an index built when a document is added and when the server starts, so that a query reads only the entries of its own terms, and SHALL find exact figures and clause numbers as written. A stored index or section file of an older format SHALL be rebuilt from the stored text on start.

#### Scenario: A 500-page set
- **WHEN** the scope holds 500 pages in several documents
- **THEN** a search answers within the tested time budget

### Requirement: Ranking across a mixed set
Ranking SHALL combine the match in a section's text, in its heading path and in the document's title, SHALL fuse it with the configured vector index when there is one, and SHALL NOT fill the results from one document while another has hits of comparable score.

#### Scenario: Two documents answer
- **WHEN** a question matches the tariff table of one document and the exceptions of another equally well
- **THEN** the top results contain sections from both

### Requirement: Outline and neighbours
The knowledge base SHALL give, without a model call, each document's outline (heading paths with pages and sizes) and the sections next to a given section.

#### Scenario: Planning a deep run
- **WHEN** a deep run plans its sub-questions
- **THEN** it reads the outlines of the documents in scope, not their text

### Requirement: What a question's words count for
The small words of a question (articles, question words, auxiliaries, in the languages the product ships) SHALL NOT rank a section; figures and codes in the question SHALL always count. Every piece of a table that is cut into several sections SHALL start with the table's header row. The document's name SHALL stand at the top of every section's heading path, whether or not the file has a title line of its own.

#### Scenario: A row of a long table
- **WHEN** a table of 80 sites is cut into several sections and the question asks what guarding site MR-061 has
- **THEN** the section with that row is found, because it carries the header "Guarding"

