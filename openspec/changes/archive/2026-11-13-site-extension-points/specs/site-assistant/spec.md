## ADDED Requirements

### Requirement: Host context and instructions per run
`SiteGuide` SHALL accept `context` (a function of the run's context returning text, sync or async), `instructions`, `style` and `history`. The text from `context` SHALL be in the site agent's prompt on every turn, under the business's instructions' priority. `style` SHALL replace the default reply length rule; `history` SHALL set how many past turns the site agent sees. A failing `context` SHALL leave the prompt without it and the turn SHALL go on.

#### Scenario: Live facts
- **WHEN** `context` returns "Open today 12:00 to 23:00" and the user asks when the place opens
- **THEN** the prompt holds that text and the agent can answer without a search

### Requirement: The host's object per request
`run(..., host=obj)` SHALL pass `obj` to every callback (in the run's context); `create_site_router(site, host=fn)` SHALL build it from each request with `fn(request)`.

#### Scenario: One guide, many sites
- **WHEN** two requests carry different `host` objects
- **THEN** each turn's `context`, tools and `form_for` get their own request's object

### Requirement: Host tools
`SiteGuide(tools=[SiteTool(name, description, parameters, handler)])` SHALL bind those tools to the site agent next to its own. `handler(args, ctx)` SHALL return the text the model gets, sync or async. A handler that raises SHALL give the model an error text and the turn SHALL go on.

#### Scenario: A host tool
- **WHEN** the model calls the host tool `site_stats` with `{days: 7}`
- **THEN** the handler gets the args and the run's context, and its text is the tool result

### Requirement: Suggestions from the site agent
With `suggestions=True` the site agent SHALL have a `suggest_next(options)` tool, and after its answer the run SHALL emit CUSTOM `suggestions {items}` with up to three options. It SHALL NOT emit them when the turn handed over to a form.

#### Scenario: Next steps
- **WHEN** the site agent answers and calls suggest_next with two options
- **THEN** the run ends with a `suggestions` event of those two items

### Requirement: Hand-off in the same run
When `SiteGuide(form_for=fn)` returns a form state for the form of `open_form`, the site agent's turn SHALL end after that call, the run SHALL emit `site_directive {type: navigate, path, form_id, handoff: "done"}`, and the form agent SHALL answer in the same stream with the hand-off message, with one `RUN_STARTED` and one `RUN_FINISHED` for the whole run. The page SHALL NOT start its own hand-off run for such a directive.

#### Scenario: Booking from the home page
- **WHEN** on the home page the user says "book me a haircut on Friday" and `form_for` builds the booking form
- **THEN** one run carries the site agent's open_form, the navigate directive with `handoff: "done"`, and the form agent's card

### Requirement: Hand-off by the page without form_for
When `form_for` is not set or returns nothing, the hand-off SHALL work as before: the note is kept and the page's next run with `handoff: true` gives it to the form agent.

#### Scenario: A host without form_for
- **WHEN** the site agent calls open_form and the guide has no `form_for`
- **THEN** the run ends with the navigate directive without `handoff`, and the page's next run delivers the note

### Requirement: The user's language at the hand-off
`open_form` SHALL accept `language` (the language the user writes in), and the hand-off message SHALL tell the form agent to reply in it.

#### Scenario: A Russian conversation
- **WHEN** the user writes in Russian and the site agent opens the loan form with `language: "Russian"`
- **THEN** the form agent's first message says to reply in Russian

### Requirement: Routing by who spoke last
On a form page, a typed message SHALL go to the router model (not straight to the form agent) when the site agent spoke last, or when it has navigation words in German, Spanish, French, Italian, Russian or Ukrainian. The router model's prompt SHALL say who spoke last and quote the end of what they said.

#### Scenario: Answering the site agent on a form page
- **WHEN** on the loan form the site agent asked "Which page do you need?" and the user replies "contacts"
- **THEN** the router model decides, and the site agent answers
