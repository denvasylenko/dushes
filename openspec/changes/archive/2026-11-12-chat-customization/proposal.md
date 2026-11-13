# Proposal

## Why

Hosts embed `<agui-chat>` into their own products. Today they can change tokens, themes and the parts on a few elements, and replace whole cards. Everything else is fixed: most elements (options, calendar days, steppers, review rows, receipts, the empty chat) have no `part`, there are no per-component tokens, icons are built in, and there is no way to put one's own component in place of a message, the header, the empty chat, an error or the composer. The goal: every element can be restyled, and every visible piece can be replaced.

## What Changes

- **Parts everywhere.** Every element the widget draws gets a stable `part` name from one documented vocabulary (`card`, `card-question`, `option`, `calendar-day`, `button-primary`, ...). Page CSS styles them with `::part()`; theme CSS uses the same names as `[part~="..."]`.
- **Component tokens.** Besides the global tokens, each component reads its own (`--agui-card-bg`, `--agui-bubble-user-bg`, `--agui-chip-radius`, `--agui-button-bg`, `--agui-input-bg`, ...), falling back to the globals; themes accept them as short keys.
- **Icons.** `icons: {send, stop, mic, clip, plus, close, logo}` replaces any built-in icon (an SVG string or an element).
- **Slots.** `render: {markdown, assistant, user, empty, header, error, suggestions, sources, composer}`: a function returns the host's own element for that piece, or nothing for the default. `markdown` also drives streaming. The formguide plugin uses `render.sources`.
- **React.** `reactSlot(Component)` turns a React component into a slot function.
- Cards stay replaceable through the existing renderer registry; the card building blocks (calendar, options, fields) are exported for custom cards.

## Capabilities

### Modified Capabilities
- `chat-widget`: parts vocabulary, component tokens, icons, slots.

## Impact

- Widget: `src/parts.ts` (new), `element.ts`, `styles.ts`, `themes.ts`, `types.ts`, `react.ts`, `formguide/index.ts`; tests.
- Docs: `site/` frontend themes and widget pages, the reference.
