# dushes Specification

## Purpose
One assistant for a whole site above the UI agent: routing each turn to Dushes or the unchanged UI agent, navigation checked against a site map, and the hand-off of a request to a form.

## Requirements

### Requirement: One assistant for a site
`Dushes` SHALL answer a run for a site page: state `{page: {path, title?}, form?: <the UI agent's state>}`. It SHALL route each turn to the UI agent (`FormGuide.run`, unchanged, with thread id `<site thread>-<form id>`) or to Dushes, and stream that agent's AG-UI events.

#### Scenario: A page without a form
- **WHEN** the user asks a question on the FAQ page
- **THEN** Dushes answers it

#### Scenario: A form page
- **WHEN** the user on the loan form page writes "my name is Anna Smith"
- **THEN** the UI agent handles the turn with its own tools and cards

### Requirement: Routing on a form page
On a page with a form, an explicit move (go to, open the ..., take me) SHALL go to Dushes, and a card answer or any message that names nothing outside the page SHALL go to the UI agent. A message that names another page's title or keywords without asking to move is unclear: a cheap router model SHALL answer one word, form or site, and on any failure the turn SHALL go to the UI agent.

#### Scenario: Leaving the form
- **WHEN** the user on the loan form page writes "open the contacts page"
- **THEN** Dushes handles it and sends a navigate directive to /contacts

#### Scenario: The form's own words
- **WHEN** the user on the loan form page writes "a car loan please", which is also a word of the Loans page
- **THEN** the router model decides form and the UI agent proposes the loan type

### Requirement: A line that names another page goes to Dushes
On a page with a form, a message that says the whole title of another page of the site SHALL go to Dushes, whatever else it says and whether or not it asks to move. The UI agent, which does not see the site, SHALL NOT be the first to get such a line. This is decided in code, with no model call.

#### Scenario: Car insurance asked from the loan form
- **WHEN** the person on the loan form says "can you open car insurance", and Car insurance is a page of the site
- **THEN** Dushes gets the line and opens that page; the UI agent is not asked

#### Scenario: The person insists
- **WHEN** the person then says "yeah, I said car insurance"
- **THEN** Dushes gets that line too

### Requirement: A spoken unclear message is routed by a rule
In a voice conversation an unclear message SHALL be placed with no model call. A move, a question, words about another page, or an answer to what Dushes just asked or offered SHALL go to Dushes; a message that names a field of the form, and any other statement, SHALL go to the UI agent. Whoever gets the message can still give it to the other in the same run.

#### Scenario: A spoken value after Dushes spoke
- **WHEN** Dushes answered last and the person says "fifty thousand" in a voice conversation on the loan form page
- **THEN** the UI agent gets the message and no router model call is made

### Requirement: Navigation checked against the site map
Dushes' `navigate` and `open_form` SHALL accept only paths, tabs, sections and forms from the site map; anything else SHALL be refused to the model. A valid call SHALL emit CUSTOM `site_directive {type: "navigate", path, tab?, section?, form_id?}`.

#### Scenario: An invented page
- **WHEN** the model calls navigate with "/careers", which the map does not have
- **THEN** no directive is sent and the model is told the page does not exist

### Requirement: Hand-off to a form
`open_form(form_id, note)` SHALL navigate to the form's page and keep the note. The next run on that page with `forwardedProps.handoff` SHALL give the UI agent the note as its first message (marked as handed over by Dushes), so it proposes the fields the note covers.

#### Scenario: From the home page to the loan form
- **WHEN** the user on the home page writes "I want a car loan of 900 000 for 3 years"
- **THEN** the chat navigates to the loan form, and the UI agent's first turn proposes the loan type, amount and term

### Requirement: Answers from the site
Dushes SHALL answer only from the site map's sections and name the page it used; when the sections do not answer, it SHALL say so.

#### Scenario: A question about opening hours
- **WHEN** the user asks when the branch is open
- **THEN** the answer comes from the contacts page and the reply offers to go there

### Requirement: Files on a form page
Files the chat uploads on a form page SHALL reach the UI agent: before a form turn, `Dushes` SHALL make the files named in the form state's `attachments` and in an upload card's `attachment_ids` available in the form's own conversation, under the same ids. Attachment storage SHALL accept the same conversation ids as the rest of formguide (letters, digits, `_`, `-`, up to 100 characters).

#### Scenario: A passport photo on the loan form page
- **WHEN** the user attaches a photo in the site chat on the loan application page
- **THEN** the UI agent can read it with extract_from_attachment

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
The site thread's transcript SHALL hold every turn the user saw, Dushes' and the UI agents' (their text), and the hand-off note, so the note survives a restart. `GET /threads/{id}?form_id=` SHALL return the messages and the open card of that form, for the page to restore the chat after a reload.

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
When `Dushes(form_for=fn)` returns a form state for the form of `open_form`, Dushes' turn SHALL end after that call, the run SHALL emit `site_directive {type: navigate, path, form_id, handoff: "done"}`, and the UI agent SHALL answer in the same stream with the hand-off message, with one `RUN_STARTED` and one `RUN_FINISHED` for the whole run. The page SHALL NOT start its own hand-off run for such a directive.

#### Scenario: Booking from the home page
- **WHEN** on the home page the user says "book me a haircut on Friday" and `form_for` builds the booking form
- **THEN** one run carries Dushes' open_form, the navigate directive with `handoff: "done"`, and the UI agent's card

### Requirement: Hand-off by the page without form_for
When `form_for` is not set or returns nothing, the hand-off SHALL work as before: the note is kept and the page's next run with `handoff: true` gives it to the UI agent.

#### Scenario: A host without form_for
- **WHEN** Dushes calls open_form and the guide has no `form_for`
- **THEN** the run ends with the navigate directive without `handoff`, and the page's next run delivers the note

### Requirement: The user's language at the hand-off
`open_form` SHALL accept `language` (the language the user writes in), and the hand-off message SHALL tell the UI agent to reply in it.

#### Scenario: A Russian conversation
- **WHEN** the user writes in Russian and Dushes opens the loan form with `language: "Russian"`
- **THEN** the UI agent's first message says to reply in Russian

### Requirement: Routing by who spoke last
On a form page, a typed message SHALL go to the router model (not straight to the UI agent) when Dushes spoke last, when it has navigation words in German, Spanish, French, Italian, Russian or Ukrainian, or when it asks where the business is or how to reach it (address, location, phone, opening hours). The router model's prompt SHALL say who spoke last and quote the end of what they said.

#### Scenario: Answering Dushes on a form page
- **WHEN** on the loan form Dushes asked "Which page do you need?" and the user replies "contacts"
- **THEN** the router model decides, and Dushes answers

### Requirement: Questions about something else on a form page
On a form page, a typed question (ending with "?" or starting with a question word in any of the widget's seven languages) that names none of the form's field labels SHALL go to the router model. Function words and question words in labels ("How many vehicles", "I have additional income") SHALL NOT count as naming a field.

#### Scenario: A question about something else on a form page
- **WHEN** on the loan form the user asks "How many new requests do I have?"
- **THEN** the router model decides instead of the UI agent answering

#### Scenario: A question about a field
- **WHEN** on the loan form the user asks "What is the maximum loan amount?"
- **THEN** the UI agent answers

### Requirement: The UI agent gives a foreign message back
Under Dushes the UI agent SHALL have a `hand_back(reason)` tool (Dushes adds the capability `hand_back`; every other client, older ones included, SHALL NOT get it). When the UI agent calls it, its turn SHALL end without more model calls, and Dushes SHALL answer the same message in the same run, with one `RUN_STARTED` and one `RUN_FINISHED`; the `hand_back` event SHALL NOT reach the client.

#### Scenario: Gift cards asked on the loan form
- **WHEN** on the loan form the user writes "tell me about gift cards" and the router gives it to the UI agent
- **THEN** the UI agent calls hand_back and Dushes answers about the barbershop's gift cards in the same run

#### Scenario: A page without Dushes
- **WHEN** the UI agent runs on its own page through `/agent/run`
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

### Requirement: Dushes gives a form question to the form
On a page with a form, Dushes SHALL have a `to_form(reason)` tool: its turn ends and the UI agent answers the same message in the same run, with one `RUN_STARTED` and one `RUN_FINISHED`. Dushes SHALL NOT have it off a form page or for a message the UI agent has just given back with `hand_back`, so a message never bounces twice. Dushes' prompt SHALL say never to send the user to another assistant.

#### Scenario: A form tab asked on the form page
- **WHEN** on the loan form a question about the locked Collateral tab reaches Dushes
- **THEN** Dushes calls to_form and the UI agent explains the tab in the same run

### Requirement: No arithmetic on prices and rates
Dushes' prompt SHALL say not to add up discounts or work out a price, rate, payment or total, but to quote each condition as the page or document states it, with what it applies to, and to say the final figure comes from the form or the business. Checking the user's own arithmetic on figures the site gave SHALL be allowed, with what it leaves out, and Dushes SHALL NOT send the user to sources the site never names.

#### Scenario: Two discounts
- **WHEN** the user asks for the rate with a salary-client discount and a life-insurance discount
- **THEN** Dushes quotes both conditions and what they apply to and does not state a combined rate


### Requirement: A move on a form page
On a page with a form, an explicit move ("take me", "navigate", "go to") SHALL go to Dushes only when it names another page of the site; when it points back into the conversation ("there", "here") or uses a word of this form's fields, it SHALL go to the UI agent, which shows the place in the form; otherwise the router model SHALL decide.

#### Scenario: Navigate me there
- **WHEN** on the insurance quote page the user says "can you navigate me there?" after the UI agent named a section
- **THEN** the UI agent answers and highlights that section, and the user stays on the page

### Requirement: One tool list per form conversation
Every UI-agent turn in one conversation (a typed message, a message given by to_form, a hand-off) SHALL offer the same tools, hand_back included; a UI agent that hands back a message given by to_form SHALL let Dushes answer it, without to_form.

#### Scenario: Thinking blocks stay valid
- **WHEN** a conversation mixes typed form turns, to_form turns and a hand-off
- **THEN** the UI agent's tool list is the same in every turn and the provider accepts its earlier reasoning

### Requirement: A spoken question is answered in one call
In a voice conversation Dushes SHALL be given, before its first model call, the passages found by the person's own words and the whole text of the page the person is on and of the pages the best passages come from (three pages at most), so that a plain question needs no reading step.

#### Scenario: Opening hours asked aloud
- **WHEN** the person asks aloud when the branch is open on Saturday and the Contacts page states it
- **THEN** Dushes answers from the page text it was given, without calling read_page or search_site

### Requirement: A question is answered before anything opens
The site agent SHALL open a page or start a form only when the person's own message asks for it (a request such as "open…", "show me…", "take me…", "I want…", "book me…", or the same as a polite question, "can you open…") or says yes to an offer made in the previous answer. This SHALL be decided in code from the person's words: a `navigate` or `open_form` call for any other message is refused, and the model is told to answer first and offer.

#### Scenario: How do I get it
- **WHEN** the person asks "how can I get car insurance?" and the model calls `open_form` for the insurance form
- **THEN** no form opens, the answer explains how, and it ends by offering to open the insurance form

### Requirement: An order to change something starts the form
A message that tells the assistant to change something (change, set, add, remove and the like, in the languages the product ships) SHALL count as a direct request for what a form does: an `open_form` call for it starts the form. A question that uses such a word stays a question, and a page still opens only when asked.

#### Scenario: New opening hours
- **WHEN** the person writes "Change the Sunday hours to 10-22" and the model calls `open_form` for the form that holds the hours
- **THEN** the form starts with that note, and no offer is made instead

### Requirement: A refused move still reads the page
A refused `navigate` or `open_form` SHALL return what that page says: the tab or section the call named, or the whole page when it named none (cut to a fixed length). The site agent answers from it with the fact the person asked about, and the person stays where they are.

#### Scenario: The price is on a tab of another page
- **WHEN** the person asks what car insurance costs and the model calls `navigate` for the insurance page's price tab
- **THEN** nothing opens, the tool result carries the tab's text, and the answer gives the price before the offer

### Requirement: A page is read without being opened
The site agent SHALL have a read-only tool, `read_page` (a page path, optionally a tab, accordion or section id), that returns what is written there and sends no directive and no offer. The agent's instructions SHALL require reading the section that would hold an answer before saying it was not found or offering to open that section.

#### Scenario: The fee is in a section of another page
- **WHEN** the person asks what a renewal costs and the site contents list a Fees section on the renewal page
- **THEN** the agent reads that section, answers with the fee, and the person stays on their page

### Requirement: An offer made in words counts
An answer that ends with a question SHALL count as an offer, whether or not a move was refused in that turn: the next message may be a plain yes to it. A one-word "open it" in the product's languages SHALL count as a direct request.

#### Scenario: A yes in Spanish
- **WHEN** the answer ends with a question offering the insurance form and the person replies with a yes and "open it" in Spanish
- **THEN** the form opens

### Requirement: The offer is one tap away
When opening was refused, the turn's suggestions SHALL start with a button that asks for it in the person's language ("Open Car insurance"), and a `CUSTOM site_offer` event SHALL name what was offered. The next message opens it when it is that button's text, another direct request, or a plain yes.

#### Scenario: The person taps the offer
- **WHEN** the previous answer offered the Contacts page and the person taps "Open Contacts"
- **THEN** the page opens

### Requirement: Dushes sees a real stretch of the conversation
Dushes SHALL be shown the latest entries of the site conversation, up to 40 and as many of the newest as fit about 24,000 characters, never fewer than the last six. When older turns are left out, it SHALL be told the person's first message of the conversation in one line.

#### Scenario: What was my first message
- **WHEN** the person asks for their first message after eight exchanges
- **THEN** that message is among the messages the model is shown

#### Scenario: A very long conversation
- **WHEN** the conversation is longer than the budget
- **THEN** the newest turns are shown and the first message is told in one line

### Requirement: The server keeps the trail of pages
For every run, on every host, the server SHALL keep the pages of the site a conversation has been on, oldest first, and SHALL tell Dushes the trail and the page before the current one. A host SHALL NOT need to send or keep it. A path that is not a page of the site SHALL NOT enter the trail.

#### Scenario: Where was I before
- **WHEN** the person went from Home to Loans to Car insurance and asks where they were before
- **THEN** Dushes is told the trail and that the page before this one is Loans

