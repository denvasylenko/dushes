## MODIFIED Requirements

### Requirement: Answers from the docs only
The docs assistant SHALL answer a question using passages retrieved from the documentation corpus, include copy-paste code when the question is about usage, and end with links to the pages it used. When the corpus has nothing relevant it SHALL say so and point to the closest page instead of guessing. Every question SHALL also carry the documentation's table of contents (each guide page's title, address and summary), so a question about where something is documented is answered with links to those pages first.

#### Scenario: A configuration question
- **WHEN** a reader asks "How do I use Azure OpenAI for the agent and a cheaper model for research?"
- **THEN** the answer contains a YAML `models:` snippet with both roles and a link to the models guide

#### Scenario: Where is it documented
- **WHEN** a reader asks "where can I see all the ways to set a model?"
- **THEN** the model receives the table of contents, and the answer starts with a link to the models guide
