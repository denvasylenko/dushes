## ADDED Requirements

### Requirement: Decisions as cards
The system prompt SHALL instruct the model to ask a yes/no or pick-one decision with `ask_user` (or to propose the change directly), not as a question in prose, and to put one short sentence that answers the user before a card instead of sending a card alone.

#### Scenario: A shorter term
- **WHEN** the agent notices that a 36-month term would satisfy a rule
- **THEN** it asks "Switch the term to 36 months?" as a question card with options, or proposes the term change, rather than ending its text with that question
