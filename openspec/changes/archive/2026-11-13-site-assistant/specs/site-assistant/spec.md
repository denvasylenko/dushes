## ADDED Requirements

### Requirement: One assistant for a site
`SiteGuide` SHALL answer a run for a site page: state `{page: {path, title?}, form?: <the form agent's state>}`. It SHALL route each turn to the form agent (`FormGuide.run`, unchanged, with thread id `<site thread>-<form id>`) or to the site agent, and stream that agent's AG-UI events.

#### Scenario: A page without a form
- **WHEN** the user asks a question on the FAQ page
- **THEN** the site agent answers it

#### Scenario: A form page
- **WHEN** the user on the loan form page writes "my name is Anna Smith"
- **THEN** the form agent handles the turn with its own tools and cards

### Requirement: Routing on a form page
On a page with a form, a message about another page or about navigating SHALL go to the site agent; any other message, and every card answer, SHALL go to the form agent.

#### Scenario: Leaving the form
- **WHEN** the user on the loan form page writes "open the contacts page"
- **THEN** the site agent handles it and sends a navigate directive to /contacts

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
