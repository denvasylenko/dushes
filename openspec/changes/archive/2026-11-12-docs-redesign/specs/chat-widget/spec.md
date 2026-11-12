## ADDED Requirements

### Requirement: Code blocks in answers
The widget SHALL render fenced code blocks (```` ```lang ````) in assistant messages as a monospace block that keeps line breaks and indentation, shows the language, and has a copy button labelled in the chat's language. Tapping it SHALL put the block's text on the clipboard and say "Copied" briefly. A fence still open while the answer streams SHALL already show as code.

#### Scenario: Copying a snippet
- **WHEN** an answer contains a ```` ```yaml ```` block and the user taps its copy button
- **THEN** the clipboard holds exactly the YAML, and the button reads "Copied" for a moment
