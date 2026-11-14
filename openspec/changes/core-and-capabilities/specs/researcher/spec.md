## ADDED Requirements

### Requirement: A generic Researcher with toolsets
The document researcher SHALL become `Researcher`: an isolated sub-agent that reads and returns a brief answer with sources, with toolsets. The `documents` toolset SHALL behave as the document researcher does today.

#### Scenario: A question about a policy
- **WHEN** the agent asks the Researcher about a cancellation policy
- **THEN** it reads the documents in its own context and returns a short answer with sources

### Requirement: The data toolset is opt-in
A `data` toolset MAY run SQL or pandas in a host-provided sandbox over data returned by the host's tools with the user's rights; it SHALL NOT open a database connection itself and SHALL be unavailable without a sandbox.

#### Scenario: No sandbox
- **WHEN** a host lists the `data` toolset without a sandbox
- **THEN** start-up fails with a clear error
