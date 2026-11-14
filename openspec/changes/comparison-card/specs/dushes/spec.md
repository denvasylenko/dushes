# Spec Delta

## ADDED Requirements

### Requirement: Questions and comparisons from Dushes
Dushes SHALL be able to ask the user with the question card (`ask_user`, as the form agent's, answered `{answer}`) and to show a comparison card. A question SHALL end Dushes' turn and its answer SHALL resume it. Dushes SHALL ask at most three questions before recommending.

#### Scenario: Which loan suits me
- **WHEN** the user on the home page asks "which loan suits me?"
- **THEN** Dushes asks what the loan is for with a question card, then shows a comparison with a recommendation
