## ADDED Requirements

### Requirement: A public field highlight
The widget SHALL export `highlightField(target, opts?)` from `@formguide/agui-chat/highlight` (and as `AguiChat.highlightField` in the one-script build). A string target SHALL be found as `[data-name]`, then `[name]`, and an input inside a `[data-name]` box SHALL ring the box. Calling it again on the same field SHALL restart the effect, and it SHALL return a function that cancels it.

#### Scenario: A host highlights its own field
- **WHEN** a page without the chat calls `highlightField("amount")` and its amount box carries `data-name="amount"`
- **THEN** the box is ringed and blinks green, and the effect ends by itself

### Requirement: Changed and look-here highlights
`kind: 'changed'` (the default) SHALL only mark the field; `kind: 'look'` SHALL also scroll to it, focus it (not on a touch device) and show `hint` as a small pill inside the field's top-right corner (`hintAt: 'below'`, or a field too small to hold it, puts it in a bubble under the field). The hint SHALL fade out after about 4 seconds and go at the user's next tap or key or the next highlight.

#### Scenario: Look here
- **WHEN** `highlightField("email", {kind: "look", hint: "As on your ID"})` is called
- **THEN** the page scrolls to the email box, focuses it and shows the hint in the box's top-right corner, gone after about 4 seconds

### Requirement: The highlight is styled by attributes and variables
For the length of the effect the field SHALL carry `data-agui-highlight` (`changed` or `look`) and `data-agui-highlight-style` (`ring`, `glow` or `pulse`), and SHALL be drawn from `--agui-highlight-color`, `--agui-highlight-width`, `--agui-highlight-mix`, `--agui-highlight-radius`, `--agui-highlight-ms` and `--agui-highlight-count`. The function SHALL add its own stylesheet, to the document or to the shadow root holding the target, so a host needs no CSS setup.

#### Scenario: A host's colour
- **WHEN** a page sets `--agui-highlight-color` and the agent changes a field
- **THEN** the field is ringed in that colour

### Requirement: Shared tokens come first
Where the page sets the shared `--hf-*` tokens (herefront-ui), they SHALL take precedence over the widget's variables: `--hf-ok` for a changed field's colour and `--hf-accent` for look, `--hf-hl-w`, `--hf-hl-mix`, `--hf-hl-dur` and `--hf-motion-ease`. Without them the highlight SHALL look as it does today.

#### Scenario: Inside a Herefront product
- **WHEN** the page carries herefront-ui's tokens and the agent changes a field
- **THEN** the ring takes `--hf-ok` and `--hf-hl-w` instead of the widget's own values

### Requirement: The highlight respects reduced motion
With `prefers-reduced-motion` a highlighted field SHALL get a steady ring for the effect's length, without a blink.

#### Scenario: Reduced motion
- **WHEN** the user prefers reduced motion
- **THEN** a highlighted field gets a steady ring for the effect's length and does not blink

### Requirement: The plugin highlights what it applies
The formguide plugin SHALL call the highlight for every field name it applies, unless its `highlight` option is false; the `agui:applied` event SHALL stay as it is.

#### Scenario: The host draws its own
- **WHEN** the plugin is created with `highlight: false`
- **THEN** applied fields are not highlighted by the widget and `agui:applied` still fires with their names

### Requirement: Thin wrappers for the highlight
The widget SHALL ship a React `HighlightTarget` (a box with `data-name`, rendered as a div unless `as` names another element) with a `useHighlight()` hook returning `highlightField`, and a web component `agui-highlight` with a `name` attribute; neither SHALL use `display: contents`. The functions, the two attributes, the six variables and the wrapper names SHALL be public API under the widget's semantic versioning; the timings and the colour shade SHALL NOT.

#### Scenario: A React field
- **WHEN** a developer wraps an input in `<HighlightTarget name="amount">` and the agent changes amount
- **THEN** the wrapper box is ringed as a widget-drawn field would be
