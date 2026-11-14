## ADDED Requirements

### Requirement: An opening turn with one tip
A run with `forwardedProps.opened: true` and no message SHALL give Dushes a `tip(topic, text, why)` tool and an internal note to say one thing worth doing now or nothing. Without a `tip` call the run SHALL end with no text. A `tip` SHALL go out as Dushes' text, with suggestions for its action and "not now".

#### Scenario: Something worth doing
- **WHEN** the host's live facts say three guest questions are unanswered and the owner opens the chat
- **THEN** Dushes says so in one or two sentences with the reason, and offers the action

#### Scenario: Nothing to say
- **WHEN** the owner opens the chat and nothing needs doing
- **THEN** the run ends without any text

### Requirement: The tips ledger
The thread's transcript SHALL keep every tip `{topic, day, status}`. `tip` SHALL be refused when `tips.per_day` tips (default 1) were shown today, when the topic was shown today, or when the user declined the topic less than `tips.snooze_days` days ago (default 7).

#### Scenario: Declined
- **WHEN** the owner answers a tip with "not now" and opens the chat the next day
- **THEN** that topic is refused for a week and Dushes may offer another one

### Requirement: A ledger and candidates from the host
`Dushes(tips_ledger=...)` SHALL read the shown and declined topics from the host's `seen(ctx)` and write every shown tip and every answer with `record(ctx, topic, declined)`, instead of the thread's transcript. `tip_candidates(ctx)` SHALL name the topics allowed now; an empty list SHALL end the opening run without calling the model, and `tip` SHALL refuse any other topic.

#### Scenario: Declined in the bot
- **WHEN** the owner taps "Not now" on the morning bot message, which the host records in its ledger
- **THEN** Dushes does not raise that topic when the owner opens the chat

#### Scenario: Nothing worth raising
- **WHEN** `tip_candidates` returns an empty list
- **THEN** the opening run ends without a model call and without text

### Requirement: Feedback on a tip
While a tip is shown and unanswered, Dushes SHALL have `tip_feedback(topic, later)` to record the user's answer, understood from any wording and language.

#### Scenario: "Maybe later" in Italian
- **WHEN** the owner answers "magari dopo" to a tip
- **THEN** Dushes records it as later and the topic is quiet

### Requirement: Cards from blocks for Dushes
`Dushes(cards=[...])` SHALL accept the same card specs as the form agent; each SHALL become a `show_<type>` tool whose card goes out as CUSTOM `card` while the turn goes on. A spec with `wait: true` SHALL be refused when Dushes is created.

#### Scenario: A reply draft
- **WHEN** Dushes calls `show_reply_draft` with a guest's name and the draft text
- **THEN** the page shows the card with the text, Copy and Send in WhatsApp

### Requirement: Sources from host tools
A `SiteTool` handler MAY return `{text, sources}`; Dushes SHALL give the model `text` and send the sources as CUSTOM `sources` once before the run ends. Dushes' prompt SHALL say that a recommendation names its source or says it is general practice.

#### Scenario: A recommendation from the week's numbers
- **WHEN** the host tool `week` returns its text with the source "Statistics, last 7 days"
- **THEN** Dushes' answer carries that source under it
