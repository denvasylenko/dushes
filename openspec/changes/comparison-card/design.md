# Design

## Context

The form agent has cards with interrupts and resume; Dushes is a plain tool loop without cards. Card specs from blocks (`card-blocks`) already turn card types into tools.

## Goals / Non-Goals

**Goals:** one new card type that both agents can use; the question card for Dushes.

**Non-Goals:** no product catalogue integration beyond host tools; no scoring formula for recommendations (the model explains its reason).

## Decisions

- **Non-blocking card.** The comparison does not interrupt the turn; the model writes one sentence with it. Tapping an action arrives as a new user turn carrying the action, like a quick reply with an `action`.
- **Dushes gets resumable questions.** Dushes' run stores the pending question in the site thread, the same way the transcript keeps the form's open card; the answer resumes with the question and answer appended to its history.
- **Sourcing rule in the prompt plus a check.** The tool result lists cells marked not stated; the eval scenarios (`scenario-evals`) include a trap for invented numbers.
- **Actions checked like navigate.** Invalid form ids or paths are refused to the model before the card goes out.

## Risks / Trade-offs

- [Wide tables on phones] → swipeable options and five criteria at most.
- [Recommendations that look like financial advice] → the reason must cite the user's own answers and the business's facts; the business's `instructions` can forbid recommending.
