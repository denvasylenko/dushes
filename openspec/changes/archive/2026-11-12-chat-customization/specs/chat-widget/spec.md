## ADDED Requirements

### Requirement: A part on every element
Every element the widget draws SHALL carry a `part` from a documented vocabulary, including card content (questions, rows, options, calendar days, steppers, review rows, receipts) and the chrome (header, empty chat, messages, steps, suggestions, composer). Parts SHALL be added to elements that appear later, such as a card's result line.

#### Scenario: Styling an option from the page
- **WHEN** the page has `agui-chat::part(option) { border-radius: 0 }` and a question with descriptions arrives
- **THEN** its options have square corners

### Requirement: Component tokens
Cards, bubbles, chips, buttons, inputs, the header, the composer and the calendar SHALL read component tokens (for example `--agui-card-bg`, `--agui-bubble-user-bg`, `--agui-chip-radius`, `--agui-button-bg`) that fall back to the global tokens. Themes SHALL accept them as short keys.

#### Scenario: Only the cards
- **WHEN** a theme sets `card-bg` and nothing else
- **THEN** cards change background and the panel keeps its own

### Requirement: Replaceable icons
The `icons` option SHALL replace any built-in icon (send, stop, mic, clip, plus, close, logo) with an SVG string or an element.

#### Scenario: A brand logo
- **WHEN** `icons: {logo: '<svg ...>'}` is set
- **THEN** the header and the floating button show that logo

### Requirement: Slots for the host's own components
The `render` option SHALL let the host replace pieces with its own elements: `markdown` (the answer's HTML, also while streaming), `assistant`, `user`, `empty`, `header`, `error`, `suggestions`, `sources` and `composer`. A slot that returns nothing, or throws, SHALL fall back to the default, with one console warning for a throw.

#### Scenario: A custom answer component
- **WHEN** `render.assistant` returns an element for a finished answer
- **THEN** that element replaces the bubble's content, and the default is used for answers it returns nothing for
