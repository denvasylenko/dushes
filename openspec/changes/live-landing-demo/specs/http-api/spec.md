## ADDED Requirements

### Requirement: Limits of the public demo
The public demo host SHALL refuse a new message over `DEMO_PER_VISITOR_DAY` messages per visitor (the `X-Demo-Visitor` header) a day, `DEMO_PER_IP_DAY` per address a day, `DEMO_PER_THREAD` per conversation or `DEMO_PER_DAY` for the whole site a day. Card answers and hand-off runs SHALL NOT count as messages.

#### Scenario: The eleventh message
- **WHEN** a visitor sends an eleventh message on the same day with the default limits
- **THEN** the run is refused with the visitor reason and the landing shows the recorded replay

### Requirement: Runs and cost of a day
The public demo host SHALL refuse any run, card answers included, over `DEMO_RUNS_DAY` runs a day or once the day's cost reaches `DEMO_COST_DAY` dollars, counted from each run's real token usage priced by `DEMO_PRICES`. Without `DEMO_PRICES` the cost cap SHALL be off.

#### Scenario: The runs of a day
- **WHEN** the day's runs reach `DEMO_RUNS_DAY`
- **THEN** the next run, a card answer too, is refused with the runs reason

### Requirement: The limit answer
A refused run SHALL get HTTP 429 with `{detail, code: "demo_limit", reason, link}` before any stream starts, where reason is one of visitor, ip, thread, site, runs, cost. `link` is `DEMO_LINK` (the quickstart).

#### Scenario: The cost cap
- **WHEN** the day's runs have cost five dollars
- **THEN** the next run gets HTTP 429 with `code: demo_limit` and the cost reason, and no model is called

### Requirement: No personal data kept by the public demo
The public demo SHALL count runs, messages, tokens and cost per day without message text, and SHALL delete its transcripts and checkpoints after `DEMO_KEEP_HOURS` hours.

#### Scenario: A day later
- **WHEN** a demo conversation is older than 24 hours
- **THEN** its transcript and checkpoint are gone and the counters keep only numbers

### Requirement: The landing's own form
The public demo host SHALL register every form in `backend/demo/landing/<form_id>.jsx` at start-up, with its domain pack from the hosted config's pack directory, and SHALL answer `GET /agent/layouts/<form_id>` for such a form with `{jsx_hash, form_id}`. The public page SHALL need no write endpoint to use it.

#### Scenario: The landing reads its hash
- **WHEN** the landing calls `GET /agent/layouts/landing_loan`
- **THEN** it gets `{jsx_hash, form_id: "landing_loan"}` and a run with that hash and form id uses the landing pack
