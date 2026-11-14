## ADDED Requirements

### Requirement: Recipes

The docs SHALL have a Recipes group in the Agents tab. Each recipe page SHALL state its goal in one line, show the full configuration, skill and tool code it needs, show what the user says and what happens, state the measured result from the evals and list its pitfalls. A recipe page SHALL link its live demo where one exists.

#### Scenario: A recipe page

- **WHEN** a reader opens a recipe
- **THEN** it shows the goal, the files, a transcript, the measured result and the pitfalls, in that order

### Requirement: Recipe results are measured

A recipe's result SHALL come from the latest eval report (runs where the expected tool was called, out of runs, with the model and date). A recipe without a report SHALL say it is not measured yet. No recipe SHALL claim a tool is always called.

#### Scenario: A measured recipe

- **WHEN** the eval report has 20 runs of the gift-card recipe and 19 called the expected tool
- **THEN** the page shows "19 of 20 runs" with the model and the run date

#### Scenario: Not measured

- **WHEN** a recipe has no eval report yet
- **THEN** the page shows "Not measured yet" and no number

### Requirement: Recipe code is the tested code

The code on a recipe page SHALL be included from the files its eval scenario runs, so the page and the scenario cannot differ.

#### Scenario: Code changes

- **WHEN** a recipe's `SKILL.md` changes in `backend/demo/recipes/<name>/`
- **THEN** the next build shows the changed file on the page
