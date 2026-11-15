## ADDED Requirements

### Requirement: Sections of large documents
A document SHALL be cut into sections on its headings and then on paragraphs to about `knowledge.chunk_chars`, with `knowledge.chunk_overlap` characters shared by neighbours; a table or a list SHALL stay whole while it fits twice that size. Each section SHALL keep its heading path, its page for a PDF and its order in the document.

#### Scenario: A clause deep in a handbook
- **WHEN** a 300-page PDF has "4.2 Late payment" under "4 Fees" on page 118
- **THEN** its section carries the path "4 Fees > 4.2 Late payment" and page 118

### Requirement: A prebuilt index
The built-in search SHALL use an index built when a document is added and loaded on start, so that a query reads only the entries of its own terms, and SHALL find exact figures and clause numbers as written. A stored index or section file of an older format SHALL be rebuilt from the stored text on start.

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
