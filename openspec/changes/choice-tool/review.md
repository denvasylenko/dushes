# Architect's review (2026-11-17)

An independent read of the first draft of this change against the code on main (not the demo branch). Verdict
on that draft: **rework**. Thirteen findings; what each led to is in the right column. The design and the spec in
this folder are the reworked ones.

| # | Severity | Finding | What changed |
| --- | --- | --- | --- |
| 1 | blocker | The draft cited a review that did not exist yet | this file |
| 2 | blocker | Dushes' history is pairs of role and text rebuilt from the transcript; it cannot hold a tool call and its result | for Dushes only the line is kept, as an ordinary assistant message; the requirement no longer asks for the tool call there |
| 3 | blocker | In the form agent a value goes tool -> card -> resume, and "applied" is known only in the resume run; the turn cannot end where the draft said | the line is written in the resume run, after "applied"; the graph changes are named (a route from the card step to the end, a written assistant message, only when the tool was the round's sole call) |
| 4 | blocker | The package's rule "the person's own words decide whether a page opens, never the model" was bypassed: the tool would let the model move on "that one" | the tool acts only when the person's own line is a request to go, or answers an offer just made (a yes, "that one", "the second"); otherwise it returns candidates and the offer |
| 5 | should fix | For screens and parts Dushes already holds the site contents and has `navigate`; the gain is from skipping the second model round, which needs no chooser | a fourth arm in the measurement: the agent's own tools with the turn ended by a server line, no chooser. The tool keeps the chooser only where it beats that arm |
| 6 | should fix | "Candidates" cannot be built from one id and one confidence; sets merge ids of different kinds; a whole form's values exceed the 255 options; checkboxes and dates do not fit | the chooser's contract gains a ranked answer; ids carry their set; too many options is its own answer, not "not found"; checkboxes are "field: yes"; dates are not the tool's |
| 7 | should fix | Text the model read (passages, documents, tool results) could drive a move; consents and fields with dependants must never be applied without the card | finding 4's gate covers moves; a value goes through the form's own change tool with all its refusals; consents and fields that restructure the form are never applied without the card; a host marks a field that submits on change |
| 8 | should fix | A turn stopped midway (voice) would leave a page opened and nothing in the history | the history line is written before the event is sent |
| 9 | should fix | The run's stats price model calls by tokens; a chooser's call has no slot; "call again narrower" can eat the rounds | a chooser kind with a per-call price in the stats; one retry of the tool a turn |
| 10 | should fix | "A plain command" against "leans on the conversation" is the very classification the layer got wrong; it is not decidable in code | said plainly: the only rule is "the layer first; no confident pick, the agent with the tool"; a miss costs the layer's fraction of a second |
| 11 | should fix | "Nothing but the phrase and the labels leaves" contradicts a description written by a model from the conversation | the data rule is restated for the tool, with what the model is told and what code checks; the untestable scenario is replaced |
| 12 | should fix | Records have no host API; each agent has its own sets; the tool must not exist when the layer is off; a host tool of the same name; the wording of the line; "opened" means "sent" | records are cut from this change; sets per agent; not bound when off; the name is reserved; the line is the label; the spec says "sent" |
| 13 | note | The measurement could not decide: no sample size for 1%, model errors mixed with chooser errors, no long-list set | the measurement section is extended |

Not accepted as written: none. Deferred to its own change: the tool given to the provider's own voice model
(finding 10's second half).

## Decisions

| Date | Who | Decision |
| --- | --- | --- |
| 2026-11-17 | the owner, through the CPO | The direction: the chooser stays in front for direct commands (open, close, go to, scroll) and is a tool for the model where things are unclear. In voice exactly as in text (option A); the tool given to the provider's own voice model is a later step, only if a measurement shows it better. |
| 2026-11-17 | the owner, through the CPO, on finding 11 (what leaves the process from the tool): "yes, with the filter" | The model may pass the chooser the target's on-screen name. The filter in code is required: a target with a phone, an e-mail, a run of seven or more digits or an item of the host's never-send list is not sent. Bookings and requests are not in this change. |
| 2026-11-17 | the CPO | The change is accepted. The tool's code is written on the demo branch first, with tests. The QA Lead measures the arms when the code is ready; the measurement's budget waits for the owner's own yes. |
