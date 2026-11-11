# Scales and tokens

The source of truth for the widget's colours is the `:host` block in `packages/agui-chat/src/styles.ts`: light and dark themes, the accent `--agui-accent`, the link colour `--agui-link`, meaning colours `--agui-ok` and `--agui-danger`. Host apps override these tokens on the element, so the widget must never hard-code a colour.

The widget has no type, spacing or radius tokens yet: use the scales below as numbers. When a task touches the shared CSS, they may be added as variables (`--agui-fs-*`, `--agui-sp-*`, `--agui-r-*`, `--agui-dur-*`).

## Colour

- One accent per screen. The accent means "press this / selected". Green and red only carry meaning (done / danger).
- Text: `--agui-ink` (main), `--agui-ink-2` (secondary), `--agui-ink-3` (captions, placeholders). Nothing paler than `--agui-ink-3`.
- Surfaces: `--agui-bg` (panel) → `--agui-surface` (card) → `--agui-soft` (user bubble, hover, fields).
- Lines: `--agui-line` (dividers), `--agui-line-2` (outlines of chips and fields). Prefer a soft shadow to a border.
- Text contrast ≥ 4.5:1, large text ≥ 3:1, in both themes. Colour is never the only carrier of meaning (a status has a word or an icon too).

## Type (the system font, SF on Apple)

| Step | px | Weight | For |
| --- | --- | --- | --- |
| caption | 11 | 600 | badges, the number keys on chips (rare) |
| footnote | 12 | 400/500 | captions under a row, the composer hint |
| sub | 13 | 400/500 | card titles, chips, buttons, step lists, field labels |
| body | 15 | 400 | messages, card content, inputs (16 on inputs on a phone, so iOS does not zoom) |
| headline | 17 | 600 | the question on a question card, the header title |
| title | 20–22 | 700 | a section title |
| large | 28 | 700 | the empty chat's greeting |

Old half steps (11.5, 12.5, 13.5, 14.5, 15.5) are moved to the nearest step when touched. Titles use `letter-spacing: -0.02em`; numbers in tables `tabular-nums`. At most 3 sizes in one card.

## Spacing (a 4 grid)

`4 · 8 · 12 · 16 · 20 · 24 · 32 · 48 · 64`. Inside a group 8–12, between groups 20–24, between sections 32–48. Panel padding: 16 on a phone, 20–24 on a computer. Related things sit closer together.

## Radii

`6` (small inner things: code, a progress bar) · `10` (fields, icon buttons) · `14` (cards, the user bubble) · `20` (panels, the composer box, the inline frame) · `999` (pill buttons, chips, avatars).
A nested radius = the outer one minus the padding (a card of 14 with 12 padding → inner elements 6–10).

## Pressable

Height: 32 (dense computer UI), 44 (phone, main buttons). Tap area ≥ 44×44 on a phone (a pseudo-element can extend it). Focus: `box-shadow: 0 0 0 3px` of the accent at low opacity, plus the accent border, visible only for keyboard focus (`:focus-visible`), never a permanent ring after a click.

## Motion

| Token | Time | Where |
| --- | --- | --- |
| instant | 100–120 ms | a tap, hover, a toggle |
| quick | 180–220 ms | a chip, a card's result line, a row expanding |
| smooth | 280–340 ms | the floating panel, a card rising in |

Curves: entering `cubic-bezier(.2,.8,.2,1)` (starts fast, lands softly); leaving `cubic-bezier(.4,0,1,1)`, a third shorter. Animate only `transform` and `opacity` (the word fade-in's blur is the one exception, kept from the Cheese chat). `@media (prefers-reduced-motion: reduce)`: no movement, only an instant change or a short fade.

## Layers

The floating panel and its scrim sit just under the top of the page's stack (`2147483000`+), because the widget lives inside unknown host pages. Inside the shadow root, keep stacking local; do not add new global `z-index` values.
