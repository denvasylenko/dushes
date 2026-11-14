# dushes Specification

## Purpose
One assistant for a whole site above the form agent: routing each turn to Dushes or the unchanged form agent, navigation checked against a site map, and the hand-off of a request to a form.

## Requirements

### Requirement: One assistant for a site
`Dushes` SHALL answer a run for a site page: state `{page: {path, title?}, form?: <the form agent's state>}`. It SHALL route each turn to the form agent (`FormGuide.run`, unchanged, with thread id `<site thread>-<form id>`) or to Dushes, and stream that agent's AG-UI events.

#### Scenario: A page without a form
- **WHEN** the user asks a question on the FAQ page
- **THEN** Dushes answers it

#### Scenario: A form page
- **WHEN** the user on the loan form page writes "my name is Anna Smith"
- **THEN** the form agent handles the turn with its own tools and cards

### Requirement: Routing on a form page
On a page with a form, an explicit move (go to, open the ..., take me) SHALL go to Dushes, and a card answer or any message that names nothing outside the page SHALL go to the form agent. A message that names another page's title or keywords without asking to move is unclear: a cheap router model SHALL answer one word, form or site, and on any failure the turn SHALL go to the form agent.

#### Scenario: Leaving the form
- **WHEN** the user on the loan form page writes "open the contacts page"
- **THEN** Dushes handles it and sends a navigate directive to /contacts

#### Scenario: The form's own words
- **WHEN** the user on the loan form page writes "a car loan please", which is also a word of the Loans page
- **THEN** the router model decides form and the form agent proposes the loan type

### Requirement: Navigation checked against the site map
Dushes' `navigate` and `open_form` SHALL accept only paths, tabs, sections and forms from the site map; anything else SHALL be refused to the model. A valid call SHALL emit CUSTOM `site_directive {type: "navigate", path, tab?, section?, form_id?}`.

#### Scenario: An invented page
- **WHEN** the model calls navigate with "/careers", which the map does not have
- **THEN** no directive is sent and the model is told the page does not exist

### Requirement: Hand-off to a form
`open_form(form_id, note)` SHALL navigate to the form's page and keep the note. The next run on that page with `forwardedProps.handoff` SHALL give the form agent the note as its first message (marked as handed over by Dushes), so it proposes the fields the note covers.

#### Scenario: From the home page to the loan form
- **WHEN** the user on the home page writes "I want a car loan of 900 000 for 3 years"
- **THEN** the chat navigates to the loan form, and the form agent's first turn proposes the loan type, amount and term

### Requirement: Answers from the site
Dushes SHALL answer only from the site map's sections and name the page it used; when the sections do not answer, it SHALL say so.

#### Scenario: A question about opening hours
- **WHEN** the user asks when the branch is open
- **THEN** the answer comes from the contacts page and the reply offers to go there

### Requirement: Files on a form page
Files the chat uploads on a form page SHALL reach the form agent: before a form turn, `Dushes` SHALL make the files named in the form state's `attachments` and in an upload card's `attachment_ids` available in the form's own conversation, under the same ids. Attachment storage SHALL accept the same conversation ids as the rest of formguide (letters, digits, `_`, `-`, up to 100 characters).

#### Scenario: A passport photo on the loan form page
- **WHEN** the user attaches a photo in the site chat on the loan application page
- **THEN** the form agent can read it with extract_from_attachment

### Requirement: The business's instructions for Dushes
The site map MAY carry `instructions`: the business's own text for Dushes. Dushes' prompt SHALL rank truth (business facts only from the site and its documents) and the site map above those instructions, and the instructions above its defaults. When Dushes ends its tool rounds without any text, it SHALL make one more call without tools so the user always gets a reply.

#### Scenario: A brief from the business
- **WHEN** the site map has `instructions: "Always mention the spring sale."`
- **THEN** Dushes' prompt carries that text under the business's instructions

#### Scenario: The rounds run out
- **WHEN** Dushes calls tools in every round and says nothing
- **THEN** it is asked once to answer without tools, and the user gets that reply

### Requirement: Dushes' knowledge
Dushes SHALL read the business documents of the site's knowledge scope (by default the "site" namespace and every form on the map): the best matching passages with every question, and the document researcher as a tool. Facts about the business SHALL come only from the site, the documents and the researcher; general concepts MAY come from general knowledge, said to be general.

#### Scenario: A partner company
- **WHEN** the user on the home page asks "What is Keystone Valuation?" and the site documents describe it
- **THEN** the answer comes from that document and names it

### Requirement: One site conversation that survives a reload
The site thread's transcript SHALL hold every turn the user saw, Dushes' and the form agents' (their text), and the hand-off note, so the note survives a restart. `GET /threads/{id}?form_id=` SHALL return the messages and the open card of that form, for the page to restore the chat after a reload.

#### Scenario: A reload on the form page
- **WHEN** the user reloads the loan form page in the middle of the conversation
- **THEN** the chat shows the whole conversation again, with the form's open card

### Requirement: Host context and instructions per run
`Dushes` SHALL accept `context` (a function of the run's context returning text, sync or async), `instructions`, `style` and `history`. The text from `context` SHALL be in Dushes' prompt on every turn, under the business's instructions' priority. `style` SHALL replace the default reply length rule; `history` SHALL set how many past turns Dushes sees. A failing `context` SHALL leave the prompt without it and the turn SHALL go on.

#### Scenario: Live facts
- **WHEN** `context` returns "Open today 12:00 to 23:00" and the user asks when the place opens
- **THEN** the prompt holds that text and the agent can answer without a search

### Requirement: The host's object per request
`run(..., host=obj)` SHALL pass `obj` to every callback (in the run's context); `create_dushes_router(site, host=fn)` SHALL build it from each request with `fn(request)`.

#### Scenario: One guide, many sites
- **WHEN** two requests carry different `host` objects
- **THEN** each turn's `context`, tools and `form_for` get their own request's object

### Requirement: Host tools
`Dushes(tools=[SiteTool(name, description, parameters, handler)])` SHALL bind those tools to Dushes next to its own. `handler(args, ctx)` SHALL return the text the model gets, sync or async. A handler that raises SHALL give the model an error text and the turn SHALL go on.

#### Scenario: A host tool
- **WHEN** the model calls the host tool `site_stats` with `{days: 7}`
- **THEN** the handler gets the args and the run's context, and its text is the tool result

### Requirement: Suggestions from Dushes
With `suggestions=True` Dushes SHALL have a `suggest_next(options)` tool, and after its answer the run SHALL emit CUSTOM `suggestions {items}` with up to three options. It SHALL NOT emit them when the turn handed over to a form.

#### Scenario: Next steps
- **WHEN** Dushes answers and calls suggest_next with two options
- **THEN** the run ends with a `suggestions` event of those two items

### Requirement: Hand-off in the same run
When `Dushes(form_for=fn)` returns a form state for the form of `open_form`, Dushes' turn SHALL end after that call, the run SHALL emit `site_directive {type: navigate, path, form_id, handoff: "done"}`, and the form agent SHALL answer in the same stream with the hand-off message, with one `RUN_STARTED` and one `RUN_FINISHED` for the whole run. The page SHALL NOT start its own hand-off run for such a directive.

#### Scenario: Booking from the home page
- **WHEN** on the home page the user says "book me a haircut on Friday" and `form_for` builds the booking form
- **THEN** one run carries Dushes' open_form, the navigate directive with `handoff: "done"`, and the form agent's card

### Requirement: Hand-off by the page without form_for
When `form_for` is not set or returns nothing, the hand-off SHALL work as before: the note is kept and the page's next run with `handoff: true` gives it to the form agent.

#### Scenario: A host without form_for
- **WHEN** Dushes calls open_form and the guide has no `form_for`
- **THEN** the run ends with the navigate directive without `handoff`, and the page's next run delivers the note

### Requirement: The user's language at the hand-off
`open_form` SHALL accept `language` (the language the user writes in), and the hand-off message SHALL tell the form agent to reply in it.

#### Scenario: A Russian conversation
- **WHEN** the user writes in Russian and Dushes opens the loan form with `language: "Russian"`
- **THEN** the form agent's first message says to reply in Russian

### Requirement: Routing by who spoke last
On a form page, a typed message SHALL go to the router model (not straight to the form agent) when Dushes spoke last, when it has navigation words in German, Spanish, French, Italian, Russian or Ukrainian, or when it asks where the business is or how to reach it (address, location, phone, opening hours). The router model's prompt SHALL say who spoke last and quote the end of what they said.

#### Scenario: Answering Dushes on a form page
- **WHEN** on the loan form Dushes asked "Which page do you need?" and the user replies "contacts"
- **THEN** the router model decides, and Dushes answers

### Requirement: Questions about something else on a form page
On a form page, a typed question (ending with "?" or starting with a question word in any of the widget's seven languages) that names none of the form's field labels SHALL go to the router model. Function words and question words in labels ("How many vehicles", "I have additional income") SHALL NOT count as naming a field.

#### Scenario: A question about something else on a form page
- **WHEN** on the loan form the user asks "How many new requests do I have?"
- **THEN** the router model decides instead of the form agent answering

#### Scenario: A question about a field
- **WHEN** on the loan form the user asks "What is the maximum loan amount?"
- **THEN** the form agent answers

### Requirement: The form agent gives a foreign message back
Under Dushes the form agent SHALL have a `hand_back(reason)` tool (Dushes adds the capability `hand_back`; every other client, older ones included, SHALL NOT get it). When the form agent calls it, its turn SHALL end without more model calls, and Dushes SHALL answer the same message in the same run, with one `RUN_STARTED` and one `RUN_FINISHED`; the `hand_back` event SHALL NOT reach the client.

#### Scenario: Gift cards asked on the loan form
- **WHEN** on the loan form the user writes "tell me about gift cards" and the router gives it to the form agent
- **THEN** the form agent calls hand_back and Dushes answers about the barbershop's gift cards in the same run

#### Scenario: A page without Dushes
- **WHEN** the form agent runs on its own page through `/agent/run`
- **THEN** it has no hand_back tool and no rule about it in its prompt


### Requirement: The names before Dushes
`formguide.site` SHALL keep `SiteGuide` and `create_site_router` as other names of `Dushes` and `create_dushes_router`, so a host written before the rename keeps working unchanged.

#### Scenario: An existing host
- **WHEN** a host imports `SiteGuide` and `create_site_router` from `formguide.site`
- **THEN** it gets `Dushes` and `create_dushes_router`

### Requirement: Form card outcomes in the site history
When the user answers a form card on a form page (a field card, a question, a confirmation, an upload), the site thread's transcript SHALL get a `card_result` entry with one line saying what happened (accepted with the values now in the form, accepted in part, rejected, skipped, the answer). Dushes SHALL see it in its history as a fact; it SHALL NOT appear among the chat's messages on restore.

#### Scenario: An accepted menu item
- **WHEN** the user accepts a card that sets Item 5 = Arrosticini and Price 5 = € 12 and then asks Dushes about the menu
- **THEN** Dushes' history holds "[Form card] Accepted, now in the form: Item 5 = Arrosticini; Price 5 = € 12" and it does not offer to add the item again

### Requirement: Staying on a form the user is filling in
With `stay_on_forms` (default true), on a page with a form Dushes' prompt SHALL tell it to answer in place and not navigate away unless the user asks to go somewhere or the business's instructions name the page for such a question. With `stay_on_forms: false` the prompt SHALL have no such rule.

#### Scenario: A studio page
- **WHEN** a host sets `stay_on_forms=False` and the owner on the "Site" page asks how many people visited
- **THEN** Dushes may open the Statistics page its instructions name

