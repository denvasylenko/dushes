## ADDED Requirements

### Requirement: A turn outlives its connection
The router SHALL run each turn as a background task and stream its events to the response. When the client disconnects, the turn SHALL continue to its end and record its result in the transcript. A new run for a thread whose turn is still running SHALL wait for that turn to end (up to 120 seconds, then end with a `RUN_ERROR` saying the previous turn is still running).

#### Scenario: The tab is closed mid-answer
- **WHEN** the client disconnects while the agent is answering
- **THEN** the turn completes and its answer and card are in the thread's transcript

### Requirement: Stop endpoint
`POST /stop` with `{thread_id}` SHALL cancel the thread's running turn and answer `{stopped: true|false}`.

#### Scenario: The user presses Stop
- **WHEN** the chat posts `/stop` for a thread with a running turn
- **THEN** the turn is cancelled and `stopped` is true
