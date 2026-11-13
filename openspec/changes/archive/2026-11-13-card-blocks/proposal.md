# Proposal

## Why

Apps that use formguide need cards of their own ("Is this your venue?", a palette to pick, "3 steps left", a booking, a route), and today the agent can show only formguide's built-in cards. Letting every host draw its own card would break the design: each would look different. Instead, cards are composed from small, configurable blocks that always look like ours (Apple, Revolut, Telegram as the bar), laid out by the developer on the server and filled with data by the model.

## What Changes

- **Blocks** (widget): small parts that compose a card: title, text, note, row (label + value, grouped like an iOS list), image, place (photo, title, subtitle, rating), stat (a big number), diff (before -> after), steps (a checklist), progress, swatches (pick a palette), choice (chips), field (an input), buttons (primary, secondary, plain) and links (call, route, website, calendar, share, copy), divider. Colours come only from the theme and a block's `tone` (accent, ok, danger, muted). A generic `blocks` card renders any list of them; answering folds it into a result line.
- **Card specs** (server): `cards:` in formguide.yaml (or `GuideConfig.cards`) declares a card: `type`, `description`, `data` (what the model fills), `blocks` (the layout, with `{name}` placeholders and `if:`), and `wait` (a question the turn waits for, or a display card the turn goes past). Each spec becomes a model tool `show_<type>`; its arguments are validated, the layout filled, and the card sent (an interrupt for `wait`, a `CUSTOM card` event otherwise). The answer comes back to the model as text: which button, which choice, which field values.
- **Capability**: the plugin announces `blocks`; a client without it never gets the card tools.

## Capabilities

- `card-blocks` (new): blocks, card specs, tools, answers.
