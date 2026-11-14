## ADDED Requirements

### Requirement: Configuration by task

The docs SHALL group configuration by the task a developer has (connect a model, their form, documents, look and feel, voice, attachments, limits and cost, history and memory, deploy). Each task page SHALL show an example before the explanation, the three to five options most people need with their defaults, both the server and the page side when the task has both, and every other option collapsed.

#### Scenario: Turning off attachments

- **WHEN** a developer opens the Attachments page
- **THEN** it shows the server key and the page attribute together, each with its default and a copyable example

### Requirement: One lookup table

The reference SHALL list every server configuration key and every widget option in one table with its side, default, task group and a link to the task page.

#### Scenario: A key's default

- **WHEN** a developer looks up `memory.keep_turns`
- **THEN** one row gives its side, default and the page that explains it

### Requirement: A quickstart that runs as written

The quickstart's code SHALL run when copied as written; any step that needs a build or a download SHALL say so and give the exact command or URL.

#### Scenario: Pasting the page example

- **WHEN** a developer pastes the quickstart's HTML into a file next to a running server
- **THEN** the chat appears without any file the page did not say how to get

### Requirement: Cost per turn

The docs SHALL give a cost per turn in dollars, computed at build time from a benchmark report and the model's price, with the date and model.

#### Scenario: Reading the cost

- **WHEN** a developer reads the Limits and cost page
- **THEN** it shows the dollar cost of each benchmark scenario with the model and the date of the run

### Requirement: A results guide per agent

Each agent (the site agent, the UI agent, the researcher) SHALL have a guide to getting good results on the developer's own setup: the host's instructions, domain knowledge, skills and tools, form integration and how to check the setup. A statement backed by a measured result SHALL say so; anything else SHALL be marked as advice.

#### Scenario: Writing the host's instructions

- **WHEN** a developer reads the UI agent's guide on instructions
- **THEN** it shows a good and a bad example, says why, and marks which points come from eval results

### Requirement: A prompt for the developer's coding agent

Every results guide SHALL offer a copyable prompt for a coding agent that lists what to collect from the project, in what form, how to wire it, and asks the agent to report what is missing.

#### Scenario: Copying the prompt

- **WHEN** a developer copies the prompt from the site agent's guide into Claude Code
- **THEN** the prompt names the site map, forms, documents and tone to collect and the pages to follow
