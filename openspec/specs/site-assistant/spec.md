# site-assistant Specification

## Purpose
One assistant for a whole site above the form agent: routing each turn to the site agent or the unchanged form agent, navigation checked against a site map, and the hand-off of a request to a form.

## Requirements

### Requirement: One assistant for a site
`SiteGuide` SHALL answer a run for a site page: state `{page: {path, title?}, form?: <the form agent's state>}`. It SHALL route each turn to the form agent (`FormGuide.run`, unchanged, with thread id `<site thread>-<form id>`) or to the site agent, and stream that agent's AG-UI events.

#### Scenario: A page without a form
- **WHEN** the user asks a question on the FAQ page
- **THEN** the site agent answers it

#### Scenario: A form page
- **WHEN** the user on the loan form page writes "my name is Anna Smith"
- **THEN** the form agent handles the turn with its own tools and cards

### Requirement: Routing on a form page
On a page with a form, an explicit move (go to, open the ..., take me) SHALL go to the site agent, and a card answer or any message that names nothing outside the page SHALL go to the form agent. A message that names another page's title or keywords without asking to move is unclear: a cheap router model SHALL answer one word, form or site, and on any failure the turn SHALL go to the form agent.

#### Scenario: Leaving the form
- **WHEN** the user on the loan form page writes "open the contacts page"
- **THEN** the site agent handles it and sends a navigate directive to /contacts

#### Scenario: The form's own words
- **WHEN** the user on the loan form page writes "a car loan please", which is also a word of the Loans page
- **THEN** the router model decides form and the form agent proposes the loan type

### Requirement: Navigation checked against the site map
The site agent's `navigate` and `open_form` SHALL accept only paths, tabs, sections and forms from the site map; anything else SHALL be refused to the model. A valid call SHALL emit CUSTOM `site_directive {type: "navigate", path, tab?, section?, form_id?}`.

#### Scenario: An invented page
- **WHEN** the model calls navigate with "/careers", which the map does not have
- **THEN** no directive is sent and the model is told the page does not exist

### Requirement: Hand-off to a form
`open_form(form_id, note)` SHALL navigate to the form's page and keep the note. The next run on that page with `forwardedProps.handoff` SHALL give the form agent the note as its first message (marked as handed over by the site assistant), so it proposes the fields the note covers.

#### Scenario: From the home page to the loan form
- **WHEN** the user on the home page writes "I want a car loan of 900 000 for 3 years"
- **THEN** the chat navigates to the loan form, and the form agent's first turn proposes the loan type, amount and term

### Requirement: Answers from the site
The site agent SHALL answer only from the site map's sections and name the page it used; when the sections do not answer, it SHALL say so.

#### Scenario: A question about opening hours
- **WHEN** the user asks when the branch is open
- **THEN** the answer comes from the contacts page and the reply offers to go there

### Requirement: Files on a form page
Files the chat uploads on a form page SHALL reach the form agent: before a form turn, `SiteGuide` SHALL make the files named in the form state's `attachments` and in an upload card's `attachment_ids` available in the form's own conversation, under the same ids. Attachment storage SHALL accept the same conversation ids as the rest of formguide (letters, digits, `_`, `-`, up to 100 characters).

#### Scenario: A passport photo on the loan form page
- **WHEN** the user attaches a photo in the site chat on the loan application page
- **THEN** the form agent can read it with extract_from_attachment

### Requirement: The site agent's knowledge
The site agent SHALL read the business documents of the site's knowledge scope (by default the "site" namespace and every form on the map): the best matching passages with every question, and the document researcher as a tool. Facts about the business SHALL come only from the site, the documents and the researcher; general concepts MAY come from general knowledge, said to be general.

#### Scenario: A partner company
- **WHEN** the user on the home page asks "What is Keystone Valuation?" and the site documents describe it
- **THEN** the answer comes from that document and names it

### Requirement: One site conversation that survives a reload
The site thread's transcript SHALL hold every turn the user saw, the site agent's and the form agents' (their text), and the hand-off note, so the note survives a restart. `GET /threads/{id}?form_id=` SHALL return the messages and the open card of that form, for the page to restore the chat after a reload.

#### Scenario: A reload on the form page
- **WHEN** the user reloads the loan form page in the middle of the conversation
- **THEN** the chat shows the whole conversation again, with the form's open card

