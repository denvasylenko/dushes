## ADDED Requirements

### Requirement: A depth per question
`researcher.depth` SHALL be `auto` (default), `quick` or `deep`. In `auto` the depth SHALL be decided in code from the person's own message, the question and a retrieval probe: deep when the message compares, asks why or how, asks for a plan or a summary, says "in detail", when the strong hits span two or more documents, or when a large document is to be summarized; quick otherwise. The decision and its reason SHALL be reported in the tool step and in `run_stats`.

#### Scenario: A plain fact
- **WHEN** the person asks "what is the late fee?" and one document answers it
- **THEN** the depth is quick

#### Scenario: A comparison
- **WHEN** the person asks "compare the Basic and Plus tariffs and explain why Plus costs more"
- **THEN** the depth is deep, and the tool step names the reason "compares"

### Requirement: Quick answers from one retrieval
In quick depth `ask_documents` SHALL make one retrieval and no model call of its own, and SHALL return the ranked passages, each with its document, heading path and page, to the calling agent, which answers with its sources. When little or nothing relevant is found, the answer SHALL say that a short look found nothing and the turn SHALL offer a "Look deeper?" suggestion, whose tap runs the same question at deep depth; quick SHALL NOT turn into deep on its own.

#### Scenario: Fee question
- **WHEN** the depth is quick and the fee is stated in one section
- **THEN** the calling agent receives that passage with its source label and answers with the figure and the source

#### Scenario: A short look finds nothing
- **WHEN** the depth is quick and no section matches the question
- **THEN** the answer says a short look found nothing, a "Look deeper?" chip is offered, and no deep run starts until the person taps it

### Requirement: Deep answers follow a fixed pipeline
In deep depth the researcher SHALL plan sub-questions from the question and the documents' outlines, retrieve for each across the documents in scope, read the found passages into notes that name their passages, make at most one more round for what is still unanswered, and write one synthesis. The order of these steps SHALL be fixed in code.

#### Scenario: Across two documents
- **WHEN** the answer needs the tariff table from one document and the exceptions from another
- **THEN** both documents are retrieved from, and the synthesis uses both

### Requirement: The shape of a deep answer
A deep answer SHALL start with a short answer of two or three sentences, continue in sections with headings, carry a citation on every claim, state for each part the documents do not answer that they do not say, and be written in the person's language. A citation that names no retrieved passage SHALL be removed, and a statement left without a citation after one repair SHALL NOT be part of the answer.

#### Scenario: A part the documents do not cover
- **WHEN** the person asks for fees and for the cancellation terms, and no document mentions cancellation
- **THEN** the answer gives the fees with citations and says the documents do not say how cancellation works

### Requirement: The deep answer reaches the person as written
The synthesis SHALL be streamed to the person as an assistant message of the run, with its sources, and recorded in the transcript as written by the researcher. The calling agent SHALL be told only that the person was answered, and SHALL NOT repeat or shorten it.

#### Scenario: A long comparison
- **WHEN** the synthesis is 400 words with four sections
- **THEN** the person sees all of it, followed by at most one sentence from the calling agent

### Requirement: Limits of a deep run
A deep run SHALL stop researching when it reaches `researcher.deep.max_seconds` or `researcher.deep.max_usd` (or `max_tokens` when no prices are configured), SHALL then write its answer from what it has, and SHALL say that the answer is partial.

#### Scenario: Time runs out
- **WHEN** the reads are not finished after the configured seconds
- **THEN** the synthesis is written from the finished notes and says it is partial

### Requirement: Progress and stop
A deep run SHALL report its progress to the client as `CUSTOM research` events with the phase (`plan`, `search`, `read`, `write`) and counts, and SHALL end when the run is stopped, keeping what was already written, marked as stopped.

#### Scenario: The person stops it
- **WHEN** the person stops the run while passages are being read
- **THEN** no further model call is made for it, and the transcript keeps the partial text marked as stopped

### Requirement: A source carries the document's own name
A source shown under an answer, and the label of a passage handed to the calling agent, SHALL name the document by its file name or title. An internal document id or a storage path SHALL never be shown; an id the model wrote in its sources SHALL be resolved to the document's name.

#### Scenario: The model cites an id
- **WHEN** the researcher's sources line says "cbde2404.md > Fees" and cbde2404 is the stored id of tariffs_2026.md
- **THEN** the source under the answer reads "tariffs_2026.md > Fees"

## MODIFIED Requirements

### Requirement: Delegated researcher with its own context
`ask_documents(question)` SHALL answer from the documents in the form's scope in its own context: whatever is retrieved and read in a deep run SHALL stay out of the calling agent's conversation, which receives the ranked passages (quick) or a one-line notice that the person was answered (deep).

#### Scenario: Long-tail question
- **WHEN** the user asks about late-payment penalties
- **THEN** the documents are searched, and the main agent's history holds only the passages it answered from or the notice
