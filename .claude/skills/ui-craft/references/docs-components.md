# The docs design system (`site/src/components/ui/`)

The docs site has one component system. Every piece of docs UI (components in `site/src/components/`, MDX pages, the landing, the card gallery, the header) is built from these primitives and nothing else; Ask AI's cards in `site/src/ask/docs.ts` follow the same look through the widget's `--agui-*` tokens (the shadow DOM never sees site CSS). The live reference, with every state and a snippet, is the page **Reference → Design system** (`site/src/content/docs/reference/design-system.mdx`).

## The rule

1. Docs UI uses only `site/src/components/ui/` (import from `./ui` or `../../../components/ui`).
2. A pattern that is not there yet is added there first (component + block in `ui.css` + specimen on the design-system page), then used.
3. Component files keep only layout (grid, gaps, sizes of stages); no colours, radii, type or controls of their own.
4. Colours, sizes, radii and motion come from the `--fg-*` tokens in `site/src/styles/theme.css`; never a raw hex, `--sl-color-gray-*` or a px font size in a component.
5. Script-built DOM uses the same classes (`ui-btn ui-btn--gray`, `ui-chip`, `ui-disc`, `ui-code-pre`…), and the helpers in `ui/ui.ts` (`copyText`, `setChoice`, `syncRange`).

## Files

| File | What |
| --- | --- |
| `ui.css` | every primitive's styles (global, loaded through `customCss` in `astro.config.mjs`) |
| `ui.ts` | behaviour by event delegation: choice groups (`[data-ui-choice]`, fires `ui-change`), menus (`[data-ui-menu]`), copy buttons (`[data-ui-copy]`), sliders (`.ui-range`); exports `copyText`, `setChoice`, `syncRange` |
| `icons.ts`, `Icon.astro` | the icons, one stroke style on a 16 px grid, `1em`, `currentColor` |
| `index.ts` | the import point |
| `Specimen.astro` | the stage for a live example on the design-system page; `[data-ds-theme]` switches the site's theme |

## Primitives and their Apple counterparts

| Primitive | Like | Use | Classes |
| --- | --- | --- | --- |
| `Button` | iOS button styles: filled, gray, plain, borderless toolbar | `filled` = the one main action in view; `gray` secondary; `plain` a text link; `quiet` toolbar (fill on hover); `iconOnly` square; `sm` 32 / `md` 36 / `lg` 44 px, all 44 on touch | `.ui-btn` `--filled` `--gray` `--plain` `--quiet` `--icon` `--sm` `--lg` `--block` |
| `CopyButton` | the Copy action with a check | "Copied" + check in the ok colour for 1.8 s; "Select and copy" when the clipboard refuses (the caller may then open the text) | `.ui-btn[data-state=copied]`, `[data-ui-copy]`, `[data-ui-copy-label]` |
| `ChipGroup` | iOS filter chips / tokens | one value of a few short options; a radiogroup with arrow keys; `<a class="ui-chip">` for jump links | `.ui-chips` `.ui-chip[aria-checked]` |
| `Segmented` | `UISegmentedControl` | 2–5 exclusive views or modes; a track and a raised thumb | `.ui-seg` `--inline` |
| `Disclosure` | a disclosure row (Finder, Settings) | `<details>` with our chevron centred on the summary line, rotating 90°; `panel` = sunken box, the whole row is the target; slot `extra` at the row's end | `.ui-disc` `--panel` `.ui-disc-chev` `.ui-disc-body` |
| `Tile` | a grouped inset section / product tile | the surface: soft fill, 24 px (20 phone, 28 `lg`); `sunken` for code in a tile; `tint` for the page's one invitation; `flush` for a stage + meta tile | `.ui-tile` `--sm` `--lg` `--flush` `--sunken` `--tint` |
| `Callout` | the header of an iOS settings group with its icon | icon in a 40 px rounded square, a title, one or two lines | `.ui-callout` |
| `LinkCard` | a navigation row with a chevron | a whole tile that goes somewhere; the chevron moves on hover | `.ui-linkcard` `--tint` |
| `Menu` | a macOS pull-down / iOS context menu | a quiet trigger with a chevron, a popover of rows (title + line); Esc, outside tap, arrow keys | `.ui-menu` `.ui-pop` `.ui-menu-item` |
| `Range` | `UISlider` | label + value on one line, accent track up to a white thumb | `.ui-range` `.ui-range-row` |
| `Swatches` | the colour well row in iOS / macOS | a radiogroup of round colours, `any` = the system picker | `.ui-swatches` `.ui-swatch` `--any` |
| `CodePanel` | Xcode / developer.apple.com code panels | a label bar with Copy over monospace text on the sunken surface; `wrap` for prompts | `.ui-code` `.ui-code-bar` `.ui-code-pre` |
| `Summary` | an "at a glance" grouped list (App Store info rows) | the first block of a guide, under the title, lead and page actions: What / When you need it / You write, inline code in backticks or slots of the same names, optional `jump` to the example; label above value on a phone | `.ui-summary` `.ui-summary-row` `.ui-summary-jump` |
| `Entries` + `Entry` | apple.com's side-by-side product tiles ("Which iPhone is right for you") | two or three equal ways into the product under a hero (Dushes / Form assistant): icon, eyebrow, title, one-line promise, up to three points, gray "Try it live" (with `demo`) and plain "Read the guide"; never a filled button, the tiles are equal | `.ui-entries` `.ui-entry` |
| `Masonry` | Photos' grid of mixed-height tiles; Pinterest-style packing | a gallery of independent tiles of different heights (Blocks): packed into columns in reading order, one column on a phone, re-packs as a tile grows; not for tiles that open in place (the card gallery keeps its grid) | `.ui-masonry` `[data-ui-masonry]` |
| `Metrics` + `Metric` | Apple's "at a glance" figures (Health / Activity summaries, product pages' big numbers) | measured numbers: value with unit, one-line label, muted detail, optional Source link; 2-4 across, 1-2 on a phone | `.ui-metrics` `.ui-metric` |
| `Compare` | the horizontal bars in Screen Time / Battery usage | 2-6 items on one scale: ours in the accent, others muted, values at the bar ends, optional `better` caption, `unit`, `note`, `max` | `.ui-compare` |
| `SourceList` | macOS source list (Finder, Mail, Notes sidebars); on a phone, a segmented control | the topic switcher in the phone menu (a computer has the header SectionTabs): current row `--fg-accent-soft` with accent text and glyph, no icon boxes, hover a `--fg-fill` row (mouse only), `aria-current`; one segmented row on a phone | `.ui-source` `.ui-source-row` |
| `SectionTabs` | apple.com's product bar; a web local navigation | the header's second row on a computer: the site's sections as links, the current one `--fg-ink` 600 with a 2px `--fg-accent` underline and `aria-current="page"`, others `--fg-ink-2`; none current on the landing | `.ui-tabs` `.ui-tab` |
| Search (`components/Search.astro`) | Spotlight; on a phone, iOS search with Cancel | the ⌘K pill and sheet over the Pagefind index: groups Guides / Reference / Specs, recent and suggested when empty, Ask AI as the last row (only with an assistant), ↑ ↓ Return Esc; full screen on a phone | `.ui-spot` |
| `Badge` | a badge / tag | a status word or count; `accent`, `ok`, `warn` only for meaning; `mono` for a code name; `.ui-dot` for "something new" | `.ui-badge` `.ui-dot` |
| field label | a grouped-list header | above chips, a segmented control, a slider | `.ui-field` `.ui-label` |

Markdown code fences (Expressive Code) stay the code block for prose; Starlight's own `Tabs`, `Aside`, `CardGrid` and `LinkCard` stay for page structure ("Next" cards).

## Tokens (`site/src/styles/theme.css`)

`--fg-ink / -ink-2 / -ink-3`, `--fg-surface`, `--fg-sunken`, `--fg-elevated` (menus), `--fg-fill / -fill-2` (translucent: they work on any surface), `--fg-line`, `--fg-thumb`, `--fg-accent`, `--fg-on-accent`, `--fg-accent-ink`, `--fg-accent-soft`, `--fg-focus`, `--fg-ok`, `--fg-warn`, `--fg-shadow-pop`, `--fg-shadow-lift`; type `--fg-fs-caption 11 · footnote 12 · sub 13 · callout 15 · headline 17 · title 22`; radii `--fg-r-sm 6 · ctl 10 · card 14 · panel 20 · tile 24 · pill 999`; heights `--fg-h-sm 32 · md 36 · lg 44` (all 44 on `pointer: coarse`); motion `--fg-dur-instant 120ms · quick 200ms`, `--fg-ease`.

Hover styles are inside `@media (hover: hover)` so they do not stick after a tap; focus is a 3 px `--fg-focus` outline on `:focus-visible` only.

## Adding a primitive

1. Mini-brief (SKILL.md) and the Apple counterpart.
2. A block in `ui.css` from tokens, light and dark; behaviour, if any, in `ui.ts` by delegation.
3. `<Name>.astro` next to it (props, `class`, `...rest` spread onto the root so `data-*` hooks and Astro's scope reach it), exported from `index.ts`.
4. A section on the design-system page: the live specimen with its states, the snippet.
5. Check at 390 px and desktop, light and dark; `cd site && npm run build`.
