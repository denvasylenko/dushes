## ADDED Requirements

### Requirement: Turn timings
Every run SHALL measure:
- time to first token: from the start of the run to the first streamed answer text, or null when there was none;
- total time;
- each model call: duration, time to its first chunk, input, output and cache-read tokens when the provider reports them;
- each tool call: name, duration and whether it failed.

Time spent waiting for the user to answer a card SHALL not be counted: a resumed run is measured from its own start.

#### Scenario: A turn with a tool
- **WHEN** a turn calls `search_fields` once and then answers
- **THEN** its stats list two model calls, one tool call with its duration, the time to first token and the total

#### Scenario: A card in between
- **WHEN** a turn ends with a card, the user answers ten minutes later, and the resumed run takes two seconds
- **THEN** the resumed run's total is about two seconds

### Requirement: The run_stats event
Before `RUN_FINISHED` (or `RUN_ERROR`) a run SHALL send `CUSTOM run_stats` with:
- `{run_id, thread_id, ttft_ms, total_ms, model_ms, tool_ms}`;
- `models: [{ms, ttft_ms, input_tokens, output_tokens, cache_read_tokens}]`;
- `tools: [{name, ms, error}]`;
- `tokens: {input, output, cache_read}`;
- `cache_hit_rate`.

It SHALL validate as an AG-UI `CUSTOM` event.

#### Scenario: Reading the numbers in a client
- **WHEN** a client listens to the run's events
- **THEN** the last event before `RUN_FINISHED` is `run_stats` with the run's timings and token counts

### Requirement: Stats in logs and the debug endpoint
Each run's stats SHALL be written as one JSON log line on the `formguide.stats` logger at INFO. The last 20 runs of a thread SHALL be kept in memory and returned by the development-only debug endpoint.

#### Scenario: Finding a slow turn
- **WHEN** a developer opens `GET /agent/debug/{thread_id}` after a few turns
- **THEN** the response lists those turns' stats, newest last

### Requirement: Trace metadata and tracers
Every graph run SHALL carry:
- run name "formguide turn";
- tags: the form id and `formguide`;
- metadata: `thread_id`, `run_id`, `form_id`, `jsx_hash`.

LangChain tracers (LangSmith through its environment variables, or any callback handler) therefore show each turn under its conversation. A `tracing` setting SHALL accept `callbacks` (import strings of factories that return LangChain callback handlers) and extra `tags`. An unimportable callback SHALL fail configuration loading with its name.

#### Scenario: LangSmith
- **WHEN** `LANGSMITH_TRACING=true` and a LangSmith API key are set in the environment
- **THEN** each turn appears in LangSmith as "formguide turn" with the thread id in its metadata, and the turns of one conversation can be filtered by it

#### Scenario: Another tracer
- **WHEN** the configuration has `tracing: {callbacks: ["my_app.tracing:langfuse_handler"]}`
- **THEN** the handler receives every model and tool call of every turn

### Requirement: Speed budgets in the offline tests
The offline tests SHALL fail when formguide's own work for the 221-field demo loan form exceeds its budget:
- building one turn's context;
- computing the diff between two configs;
- validating a 10-field card;
- one whole scripted turn without a model.

The widget's tests SHALL have budgets for:
- rendering 200 messages;
- one typewriter frame;
- parsing 5,000 SSE events.

Budgets SHALL leave room for slow CI machines (at least 5 times the measured time on a laptop).

#### Scenario: A slow regression
- **WHEN** a change makes context building ten times slower
- **THEN** the offline test suite fails with the measured time and the budget

### Requirement: Live benchmark
A benchmark script SHALL run a fixed set of scenarios against a running server and report, per scenario and as median and p90:
- time to first token and turn time;
- tool calls and tokens;
- cache hit rate;
- an estimated cost, when a price table is given (`--prices`, per million input, output and cache-read tokens).

It SHALL save the results as JSON. It SHALL exit with an error when a `--max-ttft` or `--max-turn` threshold is exceeded, so it can gate a release.

#### Scenario: Checking a model switch
- **WHEN** the benchmark runs before and after switching the agent model
- **THEN** both runs produce comparable tables and JSON files with the same scenarios
