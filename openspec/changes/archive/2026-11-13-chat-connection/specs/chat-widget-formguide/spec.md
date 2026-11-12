## ADDED Requirements

### Requirement: Plugin requests use the chat's connection
The formguide plugin SHALL send its attachment uploads (kind `attachments`), thread restores (kind `thread`) and feedback (kind `feedback`) through `ChatApi.request`, so the host's headers, credentials, fetch and request hook apply to them.

#### Scenario: Behind authentication
- **WHEN** `headers` adds an Authorization header and the user attaches a file
- **THEN** the upload to `{base}/attachments` carries the header
