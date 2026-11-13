# Components like Apple's: the standard

**Every UI component in formguide looks and behaves like its counterpart at Apple** (iOS, iPadOS, macOS, the Human Interface Guidelines). Not "Apple-ish": someone with an iPhone should recognise the component and know without a hint what it does. Our own behaviour only where Apple has no counterpart, and then by the same principles. We follow Apple's spirit: clarity, deference to the content, depth through layers, one obvious action, everything answering at once.

Where to take "Apple" from:

| Surface | Model | Why |
| --- | --- | --- |
| The chat widget `<agui-chat>` (`packages/agui-chat`) | **iMessage**: bubbles, the composer, typing dots; the floating panel is an **iOS sheet** on phones | a conversation |
| Cards in the chat (`formguide/cards.ts`, `pickers.ts`) | **iOS inset grouped lists** (Settings) and **sheets**; pickers as iOS controls (inline date picker, stepper, segmented choice) | a decision inside a conversation |
| The demo form (`frontend/`) | **macOS System Settings** on a computer, **iOS Settings** on a phone: grouped sections, labels above or on the left, our own controls (`controls.tsx`) | filling a long form |
| The react-hook-form example (`examples/react-hook-form`) | the same as the demo form | it is a form |
| The docs site (`site/`) | **developer.apple.com**: large titles, quiet navigation, code in soft panels | developers reading |
| The landing page of the docs | **apple.com** product page: big type, sections, one button | the first impression |

Check any component with three questions: **(1)** What does it look like at Apple? **(2)** What happens on tap, hold, swipe, key? **(3)** What did I do differently, and why? No answer to (3) means: redo it.

---

## 1. Buttons

| Apple style | When | Look | Ours |
| --- | --- | --- | --- |
| **Filled** (prominent) | the one main action of a card or screen | accent fill, white text 600 | `.btn.pri` |
| **Tinted** | important, not main | soft accent fill, accent text | `.chip.act` (action chip) |
| **Gray** (bordered) | ordinary actions | hairline or soft fill, ink text | `.btn.sec`, `.chip` |
| **Plain** | tertiary, in a row, Skip, Undo | no fill, link colour | `.btn.link` |
| **Destructive** | delete, turn off | danger text; filled danger only in a confirmation | `.btn.danger` |

Behaviour (required):
- Press: `scale(.97-.98)` and a slight darkening on `:active`, back in 120 ms; it fires on release (a native button does this; do not reinvent it on `pointerdown`).
- Height 44 px on touch; 32-36 px in dense desktop panels. Shape: a capsule (`--agui-radius-pill`).
- Label: a verb and an object, one line ("Fill in 3 fields", "Set 5 years"). An icon on the left, 16-20 px, same colour.
- In progress: the label says what is happening or a small spinner inside; **the width does not jump**; a second press is ignored.
- Disabled: dimmed and not pressable, and the label or a line next to it says why ("Tick the required: 1 left").
- One Filled per card. Two Filled buttons next to each other are not allowed.

## 2. Segmented control

- For 2-5 mutually exclusive views of the same content. More than 5, or different actions: chips or a menu.
- Look: a soft track, radius 9-10; the selected segment is a white pill with a soft shadow, text 600. All segments the same width.
- The pill slides (200 ms transform) rather than blinking. Arrow keys move the choice (`role="radiogroup"`).

## 3. Switch

- Only for an on/off setting that **applies at once** (no Save). Not for actions, not for questions to the user.
- Look: track 51 x 31 (iOS) or 38 x 22 (dense), green when on, soft gray when off, a white round knob with a shadow (`--agui-knob`).
- Tap anywhere on the row; the knob travels 200 ms; an error puts it back and says so.
- A checkbox is for choosing several items in a list (field-card rows, consents), not for settings.

## 4. Inset grouped lists (the field card, the review card)

- Groups on a slightly darker background, rows 44 px and more, hairline dividers (0.5-1 px) that start after the leading icon.
- Row: label (small, gray) above or on the left, value on the right or below; a chevron `›` only when it opens something deeper.
- Group title small and gray above; an explanation small and gray below (`.card-t`, `.shared`).
- Pressing a row lights it up while pressed; the whole row is the tap target for its checkbox (`label.row`).
- In formguide: the field-change card, consents, the review card, the form status.

## 5. Sheets (the floating chat on phones)

- On a phone the chat panel slides up from the bottom: radius 20-28 on top, a 36 x 5 grabber, the page dimmed behind (`--agui-scrim`). Swipe down closes it.
- On a computer: a side panel (the current floating mode) or inline.
- Close: swipe down, tap on the dimmed page, `Esc`, the close button on the right of the header. Focus goes into the sheet, Tab stays in it, and comes back to the button that opened it.
- Motion: in 320 ms `cubic-bezier(.2,.8,.2,1)`, out 220 ms; the dimming fades.
- Not yet: the grabber and swipe-down on phones (see audit.md).

## 6. Confirmation: almost never

- Only for what cannot be undone and affects others (sending the application, cancelling a booking): `confirm_action` and the confirm card. Everything reversible happens at once with Undo.
- Look: a card naming the action on its button ("Send application"), "Cancel" as the plain button; danger red only for destructive actions.
- `window.confirm/alert/prompt` are forbidden.

## 7. Menus and action sheets

- A phone: an action sheet from the bottom, a separate Cancel group, destructive in red.
- A computer: a menu at its button ("⋯" or right click), items 13-14 px with an icon on the left, groups separated, destructive at the bottom. Arrow keys, Enter, Esc; a click outside closes it.
- No action that exists only on hover.

## 8. Notifications: result line, HUD, banner

- After an action: a result line in place with Undo (`.ok-line`), like Mail's "Undo" toast but inside the card it belongs to.
- A short confirmation on the spot (HUD): the button turns into a tick for 1.5 s ("Copied").
- No banners inside the chat; errors are a readable line with Try again.

## 9. Fields and search

- A field: soft fill, no border at rest, radius 10, 44 px tall, 16 px text; focus: background to `--agui-bg`, accent border and a soft ring. The label above (small, gray). A clear button when there is text (search).
- Search: a magnifier on the left, results as you type (debounce 250 ms), no Search button. On a phone, Cancel appears on focus.
- The right keyboard: `type=tel/email/url/search`, `inputmode`, `autocomplete`, `enterkeyhint`.
- Errors show under the field after leaving it, not while typing.

## 10. Picking a value

- Up to ~7 options: chips, or a pop-up button (current value and `⌄`, a menu with a tick on the chosen one). Hundreds: a search field with a list (`.search`).
- Numbers: a stepper (`− 2 +`) for small ranges, a slider for exploring a range, the number field's stepper on its right edge.
- Dates: quick picks first (Today, Tomorrow, the next days), then our inline calendar, which follows iOS's inline date picker (a month grid, round days, the title opens years). Times: slots as chips.
- Never the browser's chrome (spin buttons, date popups, select arrows): `references/controls.md`.

## 11. Chat (iMessage)

- The user's bubbles on the right, the assistant's text on the left without a bubble (as an assistant, not a person); bubbles radius 18-20, max width 85%.
- Typing dots while the answer is coming; text appears word by word, never jumping.
- The composer: a capsule with the field, attach on the left, mic and send on the right; send is a round filled button that is quiet while empty and becomes stop while the answer streams.
- Quick replies under the last answer as capsules; they disappear when the user writes.
- New messages scroll into view only while the user is at the bottom.

## 12. Navigation

- The demo form on a computer (macOS): tabs as a segmented or toolbar row, sections as collapsible groups, the chat as an inspector on the right.
- On a phone (iOS): one column, large title collapsing into the bar, sections as grouped lists; the chat as a sheet.
- The docs site: a sidebar (macOS), a large title, "On this page" on the right; on a phone a menu sheet.

## 13. Scrolling

- Native, with inertia; nothing captures the wheel or the swipe. Sticky section headers in long lists. A sheet blocks the page scroll under it.

## 14. Loading and empty

- A spinner only inside the pressed button or a small place. Lists or cards loading longer than 150 ms: a skeleton of the same shape.
- An empty screen: what will appear here, one sentence, one action (the empty chat with starters).

## 15. Cards and materials

- A card: the surface colour, radius 14-20, an almost invisible shadow or a hairline, inner radii smaller than outer.
- Materials (blur) only for what floats over scrolling content: headers, menus, the floating panel.
- Depth through shadow and blur, not through borders and coloured fills.

## 16. Type and icons

- The system font (`-apple-system, SF Pro`) everywhere, Inter as the fallback. The scale: `tokens.md`. Titles with negative tracking.
- Icons: line icons like SF Symbols, 1.8-2 stroke, round caps, a 24 grid, one style per product. No emoji as icons.

## 17. Motion

- Springs, not lines: in `cubic-bezier(.2,.8,.2,1)` 200-340 ms, out faster. Only `transform` and `opacity`.
- Motion explains space: a sheet comes from the bottom and leaves downward, a card folds into its result line, a chevron turns when something opens.
- `prefers-reduced-motion`: no movement, only fades.

## 18. Keyboard and screen readers

- Everything pressable is a `button` or `a`; nothing pressable inside something pressable.
- A visible focus ring only for keyboard focus (`:focus-visible`), soft accent 3 px, like macOS.
- `Esc` closes the top layer, `Enter` confirms, arrows move in lists and calendars, number keys pick options when the user works from the keyboard.
- Labels for icons (`aria-label`), roles for segments, menus and dialogs, `aria-live` for results and errors.

---

## Our classes, by component

| Component | Widget (`styles.ts`) | Demo form and examples (`controls.css`) |
| --- | --- | --- |
| Filled button | `.btn.pri` | `.submit` (example) |
| Gray / plain button | `.btn.sec`, `.btn.link` | `.ctl-file label` |
| Chips | `.chip`, `.chip.on`, `.chip.act` | radio and checkbox rows |
| Two-line option | `.opt`, `.cmp-col` | |
| Grouped list | `.card .row`, `.rev .row` | `.acc` groups |
| Field | `.text-in`, `.field input` | `.ctl-field` |
| Number stepper | `.num`, `.stepper` | `.ctl-num` |
| Select | `.sel` | `.ctl-sel` |
| Date | `.strip`, `.cal`, `.date-face` | `.ctl-date`, `.cal` |
| Result line with Undo | `.ok-line` | |

Known gaps (fix when working nearby, keep `audit.md` up to date):
- the bubble sheet on phones has a grabber but no swipe-down to close yet;
- no segmented control yet where 2-5 views of one thing are offered;
- no "⋯" menu or context menu on card rows;
- buttons have no press scale on `:active` everywhere;
- the large title of the demo form does not collapse on scroll.
