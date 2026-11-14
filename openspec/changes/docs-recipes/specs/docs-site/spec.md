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

### Requirement: Benchmark numbers come from reports

Every measured number on the Benchmarks page SHALL be read at build time from a report file under `site/src/data/benchmarks/`, written by the script that measured it, with the date, the model and, when known, the code version. The page SHALL say when and with which model they were measured, and SHALL flag a report older than 14 days.

#### Scenario: A fresh report

- **WHEN** the live benchmark report is 3 days old
- **THEN** the page shows its numbers with "Measured on <date> with <model>"

#### Scenario: An old report

- **WHEN** the live benchmark report is 20 days old
- **THEN** the page shows a note that the numbers are 20 days old and should be measured again

### Requirement: Comparisons change one thing

A comparison chart on the Benchmarks page SHALL compare runs that differ in one thing only, the same model over time or different models on the same day and code, and SHALL say which.

#### Scenario: Two models

- **WHEN** the page compares two models
- **THEN** both were measured on the same day with the same code, and the chart says so

### Requirement: Broken links fail the docs build

The docs workflow SHALL check every internal link and anchor of the built site and fail when one is broken.

#### Scenario: A renamed heading

- **WHEN** a page links to an anchor that no longer exists
- **THEN** the docs workflow fails and names the page and the link
