# Design

## Mini-brief (ui-craft)
1. **Who and why:** a developer embedding the chat in their product and brand.
2. **Main action:** one option (`theme`, `render`, `icons`) or one CSS rule per change.
3. **Ladder:** restyling an option button today needs a theme with internal class names that may change; after: `agui-chat::part(option) { ... }` or `--agui-chip-radius`.
4. **States:** a slot that throws or returns nothing falls back to the default element, with one console warning.
5. **Phone:** nothing changes by default.

## Parts from one map
`src/parts.ts` maps widget classes to part names. A MutationObserver on the shadow root adds the parts to every element as it appears (including cards that change after an answer), merged with parts set in code. The map is the documented vocabulary; class names stay internal.

## Tokens
Component tokens are read with the global as fallback: `background: var(--agui-card-bg, var(--agui-surface))`. They are not defined on `:host`, so a global change still flows through unless a component token is set.

## Slots
Each slot gets data and the chat API and returns an element or null. `markdown(text)` returns HTML and replaces `md()` for live and finished answers. `assistant(text, chat)` runs when an answer ends (and on restore) and replaces the bubble's content. `composer(chat)` replaces the composer; the host calls `chat.send()`.
