## ADDED Requirements

### Requirement: Starters
A domain pack MAY define `starters`, a list of up to 6 short opening messages in the form's main language. A pack with more than 6 starters, or with a starter that is not a string, SHALL get a validation warning.

#### Scenario: A pack with starters
- **WHEN** `loan_application.json` has `starters: ["Where do I start?", "What documents do I need?"]`
- **THEN** an empty thread for that form offers those two starters
