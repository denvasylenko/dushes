## ADDED Requirements

### Requirement: Debug view of a thread
The development-only `GET /debug/{thread_id}` SHALL return:
- the model's history for the thread;
- `runs`: the stats of the thread's most recent runs (see run-observability).

It SHALL only be mounted when the router is created with `debug=True`.

#### Scenario: Debug off
- **WHEN** the router is created with `debug=False`
- **THEN** `GET /debug/{thread_id}` is not found
