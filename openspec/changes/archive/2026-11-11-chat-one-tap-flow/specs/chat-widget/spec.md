## MODIFIED Requirements

### Requirement: Quick-reply chips
The widget SHALL show quick-reply chips: the starters for an empty chat, and the latest `CUSTOM suggestions` event under the last answer. Clicking a chip SHALL send it as a message. A suggestion with changes in `applies` SHALL be marked as filling fields; clicking it SHALL hand the changes to the plugin that applies them (formguide's `applyChanges`), show the result with Undo, and then send the text. When applying fails, the chips SHALL stay and a readable error SHALL show under them. The chips SHALL disappear when the user sends a message.

#### Scenario: A suggestion clicked
- **WHEN** the last answer has the suggestions "What comes next?" and "Fill from my passport"
- **THEN** two chips appear under it, and clicking one sends that text

#### Scenario: A chip that fills a field
- **WHEN** the user clicks "Change term to 48 months", which carries a change of the term
- **THEN** the term is filled at once, a "✓ Filled in · Loan term · Undo" line appears, and the text is sent

### Requirement: Cards closed by a new message
When the user sends a message while a card waits for an answer, the card SHALL be closed: it SHALL keep its question or title, hide its controls, and say it was replaced by the user's message.

#### Scenario: Typing instead of answering
- **WHEN** a question card is pending and the user sends "Actually, let me think"
- **THEN** the card shows only the question and "Replaced by your message"

## ADDED Requirements

### Requirement: Empty chat
An empty chat SHALL show the title, an intro and the starters. "New chat" SHALL keep the starters of the current form. Without starters, the intro SHALL not mention suggestions.

#### Scenario: New chat
- **WHEN** the user starts a new chat on a form whose pack has starters
- **THEN** the empty chat shows those starters
