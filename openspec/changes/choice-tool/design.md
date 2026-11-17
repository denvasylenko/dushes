# Design

Sources: the owner's words through the CPO (2026-11-17); the Cheese repository's `docs/proposals/jev-as-tool.md`
and D-28, D-29 (read, not edited); OpenAI's guides for the live voice model, read 2026-11-17 (live-delegation,
live-conversations, the gpt-live-1 model page); the local demo on branch `demo/jev` and what the owner's own
tests of it showed.

## The chooser first (the owner's later decisions, 2026-11-17; they replace the hybrid's gate)

After his own tests of the demo the owner changed the shape. Where this section and a later one disagree, this
section holds; the tool for the model (below) stays as designed.

1. **Every line goes to the chooser**, not only the direct commands. No name is matched in code in front of it
   ("no model" answers are gone); matching in code stays only as a switch for the measurement's "code" arm.
2. **The chooser sees what the agent sees.** The same history window, cut the same way, and the same state: the
   screen and the focus, the form's outline as its assistant reads it (personal values as "filled" / "empty"),
   the site map as paths ("Apply for a loan > Applicant > Personal details"), what was offered and opened last.
   Only the owner's filter is on top: an e-mail, a phone, a run of seven or more digits and the host's never-send
   items are replaced before anything leaves the process.
3. **The chooser picks the target**, always: a page, a tab, a section, a list option, the visible field a value
   of an obvious type is for (a date, a number, an option). Code only carries the pick out, checks the state, and
   keeps the prohibitions: a date never moves the person, a consent is never an option, only on the person's own
   request, only what can be undone.
4. **What it is sure of is applied; the rest of the line is the agent's.** Nothing left: the turn ends with one
   short line built in code, in the conversation's language (the name of what was opened, or the value set), and
   no model is called. Something left (a question, an explanation, a text to write): the agent gets the line
   with "already done: ...", does not repeat it, and answers the rest in the same run. What the chooser is not
   sure of is not applied.
5. **Free text and explanations are never the chooser's.** A text for a field (a description, an address), "why",
   "how", "what does it mean" go to the model, even when the line begins with a verb of command.
6. **"I need more context" is a structured lookup, with no text from the chooser.** An option is a pair (source,
   object of the map): "help for the field Loan type", "site knowledge: the page Car insurance". Sure of it: the
   server reads that object by its id (a read only), adds it to the chooser's state and asks once more, one
   extra round at most; then it applies or hands on. A search in free words is the model's. Behind a switch,
   off by default until the QA Lead's measurement shows the threshold holds; off, "not sure" goes to the agent.
7. **A card may be an option**: "show card X", only for cards whose data the server builds without a model.
8. **What the person sees in the demo**: the label under the turn names who did what, with times: the chooser
   alone, the model alone (and that the chooser was asked first), or both ("opened X, then the model").

Built on the demo branch so far: 1, 3, 5, the label of 8, and 4 for moves on the site (a page, a tab, a section).
Not built: 2 in full (the demo sends the last ten messages, not the agent's own window), 4 for values and for a
form's section on the screen, 6, 7.

The order of work (the owner): the chooser to a measurement first, then the factory settings; each step counts as
better only by a number against the one before.

## The hybrid (the owner's correction, 2026-11-17)

The owner: keep the chooser in front for "super direct" lines ("open, close, go to, scroll"), "plain commands";
"and where things are unclear, it would be a tool for the model". In voice and in text alike. So a line takes
one of two roads:

1. **A direct command -> the layer in front of the model, acts at once** (as `intent-layer` and the demo).
2. **Everything else -> the model, with the chooser as its tool** (this change): what leans on the conversation
   ("open it"), an order with a question in it, a line that is unclear.

**What makes a line a direct command** is decided in code first and by the chooser second; both must agree:

- in code: the line begins (after a greeting or "please", "can you") with a verb of a short list, per language:
  open, close, go to, show, scroll, switch or translate the language, set or choose a named value; it holds no
  question; it says no more than the place or the value it names (the rule the demo needed: "open personal
  details in loan application" says more than the page); it holds no date, and no name the screen does not show;
- by the chooser: it is an order, its kind is one the layer may carry out, and the place or value is picked with
  confidence at or above the act threshold, with its name said in the line;
- and the action can be undone.

One "no" on any of these and the line takes the second road. The bar for the first road does not move: sure of
every answer, and reversible. A line the code calls direct that the chooser is not sure about costs the
chooser's fraction of a second and then goes to the model, with what the chooser found handed along so the
model does not start from nothing.

The verb list is short on purpose. A new verb is added when a measured phrase needs it, never by guess.

### What the owner's own tests added (2026-11-17)

- "Open apply for loan ?" and "can you open car insurance?" are commands in a spoken or polite form: the verb at
  the start decides, a question mark at the end does not undo it, and a title is matched without its articles.
  An explicit request is never answered with "want me to open it?".
- "Open it" right after an offer is not a line for a model at all: the person agreed to exactly what was
  offered, so the server carries the offer out in code. This is the fastest road for the commonest
  context-dependent line, and it needs neither the chooser nor the tool.
- By voice, after a direct command: one short line and silence (the owner's standard: "Open Telegram" opens it
  and the voice says "done"). The voice model's own acknowledgement comes 0.8 s after the person stops; when the
  action is done before that, the server cancels it with an empty note and then gives the one line.

## The tool

```
choose_on_screen(what, among)

  what    the target by the name it has on the screen, with the conversation resolved:
          "Car insurance quote", "Personal details", "Loan type: Car loan"
  among   which options to pick from. Dushes: "screens", "parts". The form agent: "form" (its tabs and
          sections), "values" (the options of its choice fields, as "field: option"; a checkbox is "field: yes")
```

The model does not pass options: the server builds them from the site map and the form as they are now, so the
model cannot invent a target and spends no tokens on a list. Each option's id carries its set ("screen:/loans",
"part:/loans#rates", "form:acc_personal", "value:loan_type=auto"). Dates and free text are not the tool's.
The name is reserved: a host tool called `choose_on_screen` is refused when the server starts. The tool is not
offered to the model at all when the layer is off.

The chooser's contract gains a ranked answer for this: the options in order with their confidences, not one id.
The answer to the model is one of:

| `status` | Meaning | What the model does |
| --- | --- | --- |
| `done` | the first option is at or above the act threshold, well clear of the second, the action can be undone, the person's own line asked for it, and it was sent to the screen; `label` says what | nothing: the turn has ended (see below) |
| `candidates` | two or more fit, or one fits below the act threshold; up to five labels | asks one question, or calls once more with a narrower `what` (one retry a turn) |
| `offer` | the pick is clear but the person's line did not ask to go; `label` says what | answers first and offers it, as it does today |
| `not_found` | nothing among the options fits | says so and offers what exists |
| `too_many` | the set is larger than the chooser takes (a whole form's values) | names the field in `what` and calls again |
| `needs_confirmation` | the pick is clear but the action cannot be undone, or it is a consent, or a field that restructures the form | uses the card or the confirmation it already has |
| `refused` | the form or the server did not take it; `why` is the form's reason | explains and offers the nearest |
| `unavailable` | the chooser was late, failed, is off, or `what` held something that never leaves the process | does it its own way, with its other tools |

## The person's own words still decide

The package's rule stands: a page opens or a form starts only when the person's own message asks for it or
answers an offer made in the previous answer. It is decided in code from their words, never by the model. The
tool is under the same rule: it returns `done` only when the line is a request to go, or the last answer made an
offer and the line takes it up ("yes", "open it", "that one", "the second"). That is what closes the door on
text the model merely read (a passage, a document, a tool's result) moving the person somewhere.

## Two thresholds

- **Act** (high): at or above it, with the first option clear of the second by a margin, and only for the kinds
  the layer may carry out by itself (navigate, show, a field value with Undo), the server acts. The number comes from the QA Lead's measurement; the bar of D-29
  applies to it: confident wrong picks at most 1%.
- **Offer** (lower): between the two the tool returns `candidates`; below it, `not_found`.

A wrong action is worse than a question, so nothing below the act threshold is carried out, ever.

## What goes to the front end, and when

Exactly what the agents send today, so no client changes:

| Pick | Event |
| --- | --- |
| a screen | `CUSTOM site_directive {type: navigate, path}` |
| a part of a page | `CUSTOM site_directive {type: navigate, path, tab or section}` |
| a tab or section of the form | the form agent's "show where" directive |
| a value | the form agent's own change tool: its card, marked to apply at once with Undo |

A value always goes through the form agent's change tool, so every refusal it has (a read-only field, a value
the field does not take, a consent) still applies. No client acknowledges a directive today, so "opened" in this
change means "sent to the screen".

## How the turn ends without a second model call

**Dushes** (a screen, a part). The line (the label of what was opened, nothing more) is written to the
conversation first, as an ordinary assistant message; then the directive is sent; then the run ends. Written
first, so a turn stopped midway never leaves a page opened and nothing in the history. Dushes' history is text
only, so the next turn's model sees "Car insurance." as its own last words; that is enough for "and what does
full cover cost there?".

**The form agent** (a section, a value). "Applied" is known only after the card, in the resume run. So the first
run ends on the card as today; in the resume run, when the form reports the change applied with no complaint,
the server writes the line as the assistant's message and the turn ends there, by a route from the card step
straight to the end. This holds only when the tool was the only call of its round and the model wrote nothing
before it; otherwise the model speaks as usual. A refusal, an error after the change or a rejected card goes to
the model.

Nothing is said to be opened that was not sent, and nothing is said to be set before the form applied it.

The run's stats list the tool with its time, and the chooser's call as its own kind with a price per call (it has
no tokens to price by).

## Why this is better than the layer in front, and what it costs

| | The layer in front (`intent-layer`) | The tool |
| --- | --- | --- |
| A plain command ("open requests") | the chooser alone, about 0.2 to 0.4 s | the model's decision plus the chooser: about 1 to 2 s with Haiku in text |
| "Open it", "that one", "the second" | cannot; the agent's turn | the model resolves it into `what` |
| "Can you open car insurance" | the chooser read it as "not a command" in the owner's test; fixed by a code rule | the model reads it |
| A part the chooser was not shown | needed two code rules (the part's name must be said; a line that says more than the page) | the model names the part; `not_found` when it is not among the options |
| Hand-back | eight cases and their rules | the tool's answers |
| A screen or a part, for Dushes | the chooser picks it | the model already has the site's contents and a tool that opens a path: the chooser may add nothing here (see the fourth arm of the measurement) |
| Where the chooser helps most | every command | a pick from a long list (fields, bookings, menu items) |

So the two are not rivals for every phrase, and the owner's choice is the hybrid above. The measurement
checks that choice against each road alone.

## Voice: what the provider allows

Facts from OpenAI's guides (read 2026-11-17), because they bound the design:

- We connect the voice model in **client delegation**. In that mode the voice model does not call tools and
  tells us nothing of what it wants: the hand-over event "does not contain the user's utterance or task text",
  and the guide's instruction is to "use the transcript events and application state to work out what the user
  wants". The live session has no `tools` field in the guides we read.
- The other mode is **Responses delegation**: the voice model hands the request to an OpenAI Responses model,
  and tools are registered there. A function call arrives with `name` and `arguments`, our application runs it
  and returns a structured result. Latency is not stated ("compare … on your own workload"). The mode is fixed
  when the session is created.
- The session does not give the client a readable conversation: we collect the transcript of both sides
  ourselves from the events, and transcripts "may contain mistakes".

So "the voice model calls the chooser as a tool" is not literally available in the way we run voice today. The
two real shapes:

**A. Client delegation, the chooser behind our own code and agent (what the demo does, extended).** What was
heard comes to our server with the conversation we keep. A direct command goes to the chooser at once, as now.
Everything else goes to our agent, which calls `choose`. This is the hybrid, in voice. The owner's demo was this
without the tool: fast on commands, blind to "open it".

**B. Responses delegation, the tool registered with the provider's model.** The model that holds the
conversation calls `choose`; we run it and answer. This is the owner's picture exactly, but the model behind
the voice is then an OpenAI Responses model, not Haiku, for every spoken turn: a change of model, which is the
owner's decision, and an unknown latency.

B is not part of this change; when it is taken up it gets its own.

**The owner's decision (through the CPO, 2026-11-17): A.** Voice works exactly as text does: a direct command
goes straight to the layer, everything else goes to Haiku with the tool. The same in every product that uses the
package: the widget, clients' sites, the cabinet on the web and on iOS. B is a later step, taken only if a
measurement shows it better, and it needs the owner's yes to that model.

## Data

The layer's rule (only the person's phrase and the option labels leave the process) cannot hold as written for
the tool: `what` is written by a model that has read the conversation. So for the tool:

- the model is told to give the target by the name it has on the screen, and nothing else;
- code refuses to send a `what` that holds a phone, an e-mail, a digit run of seven or more, or an item of the
  host's never-send list; the tool then answers `unavailable`;
- the options are built by the server, so no form value and no page text goes out with them.

A name that the host did not list cannot be caught in code; that is why records (bookings, requests) are not in
this change: they wait for a host's own way to supply them by number or time.

## Voice: an honest note on "direct"

"A direct command" against "a line that leans on the conversation" cannot be told apart in code with certainty:
it is the classification the layer got wrong in the owner's tests. So the rule is one-way: the layer is tried
first under its strict bar; when it does not act, the line goes to the agent with the tool. A line the layer
tries and gives up on costs its fraction of a second.

## The measurement (the QA Lead's; D-23)

One set of phrases, run through each arm; the plan and the price are hers, the arms and the measures are these.

| Arm | Text | Voice |
| --- | --- | --- |
| the layer only | the demo branch's wiring; everything it does not take goes to the agent without the tool | the same, in a talking thread |
| the tool only | every line goes to Haiku, which calls `choose` | our agent calls `choose` on what was heard |
| the hybrid | a direct command through the layer, the rest to the agent with the tool | the same, in a talking thread |
| (later, on the owner's yes) | | B: the provider's model calls `choose` |

The phrases: her five sets of commands; a "holds the conversation" set (a question, then "open it", "that one",
"the second", "and the other one"); polite forms; lines that name a part the screen map does not hold; lines with
a question in them; lines that are not commands; a long-list set (a form with many choice fields, a page with
many parts), which is where the chooser is supposed to earn its call; lines in the seven languages; voice lines
as speech recognition returns them, mistakes included; a line cut off midway; and a set where the text the model
reads (a passage, a field's value) tells it to open something the person did not ask for.

One more arm, from the review: **the agent's own tools with the turn ended by a server line, and no chooser**.
Dushes already has the site's contents in its prompt and a tool that opens a path; most of the tool's speed
comes from not calling the model a second time, which needs no chooser. The tool keeps the chooser only where it
beats this arm.

The measures, per arm: the right action taken; a wrong action taken, split into "the model named the wrong
target" and "the chooser picked the wrong option" (the confidence covers only the second); "holds the
conversation" right; time from the end of the phrase to the action on the screen, p50 and p95; the price of a
phrase; how often the turn fell back to the agent. To show "at most 1% wrong" an arm needs about 300 carried-out
actions with none wrong; fewer than that shows a trend, not the bar.

The hybrid is the owner's choice; the numbers confirm it or show which road alone does better, for text and for
voice separately. The act threshold and the verb list are set from the same run: a verb whose lines the layer
gets wrong leaves the list.

## Review

An architect's review of the first draft is in `review.md` (verdict: rework), with what each finding changed.
This design and the spec are the reworked ones.
