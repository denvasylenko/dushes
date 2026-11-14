# Proposal

## Why

The owner asked (14.11, through the CTO) for a cookbook in the docs: skills and configurations as many working examples, each tested. Today the guides explain one part at a time; a reader who wants "a site with one form" or "a gift-card skill" has to assemble it from five pages, and nothing says how reliably the agent does it. An LLM cannot promise that a tool is always called, so a recipe states what the evals measured, not a guarantee.

## What Changes

- A **Recipes** group in the Agents tab: 16 recipes to start and one **Pitfalls** page; no fifth tab.
- Every recipe has the same parts: the goal in one line; the full config (`formguide.yaml`), `SKILL.md` and tool code; a short replayed transcript (what the user says, what happens); the measured result from QA's eval runs ("19 of 20 runs called `issue_gift_card`"), with the run date and model; the recipe's pitfalls; a link to its live demo where one exists.
- Every recipe is backed by an eval scenario (QA Lead) under `backend/evals/recipes/`: a recipe that breaks fails the evals. The page's number is read from the latest report, not typed by hand.
- The code on a recipe page is the code the scenario runs: the page includes it from `backend/demo/recipes/<recipe>/` instead of copying it.
- A recipe that needs a capability not shipped yet (host actions, server-declared forms, the core) waits for it; no page shows options that do not exist.

## Capabilities

- Modified: `docs-site` (a Recipes group; recipe page contract; recipe numbers from eval reports).

## Impact

- Docs Lead: the group, page template, include and number plumbing, the pages.
- QA Lead: one scenario per recipe, run in the benchmark rounds; the report carries per-recipe tool-call counts.
- Owner: the facts for the Pitfalls page; review of each recipe's code.
- Order: after the header tabs (docs-restructure task 2.1).
