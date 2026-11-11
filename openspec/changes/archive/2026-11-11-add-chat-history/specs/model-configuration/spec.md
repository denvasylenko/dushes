# Spec Delta

## ADDED Requirements

### Requirement: Persistent stores
The configuration SHALL accept a LangGraph checkpointer and a transcript store, in code or in YAML (`checkpointer: {sqlite: path}`, `transcripts: {dir: path}` or `transcripts: memory`). Without configuration, the checkpointer SHALL default to an in-memory saver and the transcript store to files under the data directory (like dependency maps, documents and attachments).

#### Scenario: Demo configuration
- **WHEN** `demo/formguide.yaml` is loaded
- **THEN** the guide uses an SQLite checkpointer and a file transcript store under `data/`
