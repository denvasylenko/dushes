# Known UI debt (as of 2026-11-11)

Found while adopting this standard. Strike out what is fixed, add new findings with a date.

## The chat widget (`packages/agui-chat`)

| What is wrong | Law | How to fix | Cost | Effect |
| --- | --- | --- | --- | --- |
| ~~A question tied to a field is followed by a field-change card for the same value: two taps, no decision in the second~~ | 2 | the question fills the field when answered (options carry the form-format value; the resume carries the new config), with Undo; clients that do not apply fall back to today's card | M | big: half the taps on choices (fixed 2026-11-11, one-tap-questions) |
| ~~12 font sizes, including 11.5, 12.5, 13.5, 14.5, 15.5~~ | 10 | move to 11 / 12 / 13 / 15 / 17 / 20 / 28 | S | medium (fixed 2026-11-11, one-tap-questions) |
| ~~9 radii, including 4, 5, 9, 12, 24~~ | 10 | move to 6 / 10 / 14 / 20 / 999 | S | medium (fixed 2026-11-11, one-tap-questions) |
| ~~About a dozen inline styles in the card renderers (`formguide/cards.ts`)~~ | 10 | classes in `styles.ts` (`.row`, `.zone`, `.bar`) | S | medium: themable by hosts (fixed 2026-11-11, one-tap-questions) |
| ~~Icon buttons (send, mic, paperclip, header) are 36 px; card links about 24 px tall~~ | 9 | 44 px tap area on touch screens (`@media (pointer: coarse)`), a pseudo-element for links | S | big on phones (fixed 2026-11-11, one-tap-questions) |
| ~~After an answer the primary button keeps a strong ring (focus moved by script looks like keyboard focus)~~ | 10 | soft `:focus-visible` ring only; do not move focus to the next card's primary on a phone | S | medium (fixed 2026-11-11, one-tap-questions) |
| ~~The run error line shows the raw server text ("HTTP 500: …")~~ | 7 | a human sentence per error kind (network, 401, 409, 429, 5xx), the raw text in `title`; keep "Try again" | S | medium (fixed 2026-11-11, one-tap-questions) |
| ~~"Fill in" does not say how much ("Fill in" for 1 field and for 7)~~ | 8 | "Fill in 1 field" / "Fill in 3 fields", "Fill in 2 of 3" when some are unticked | S | small (fixed 2026-11-11, one-tap-questions) |
| ~~The composer's send button looks primary while empty~~ | 1 | quiet until there is text (keep it pressable: an empty send shakes) | S | small (fixed 2026-11-11, one-tap-questions) |
| ~~Dependent fields need a card per level (Make, then Model: two cards, about 25 s)~~ | 2 | deferred rows: one card applies in order and looks the option up in the refreshed form | M | big (fixed 2026-11-11, chat-one-tap-flow) |
| ~~Quick replies only send text, so a reply chip costs a tap, a turn and a card~~ | 2 | action chips: a suggestion carries validated changes and fills at once, with Undo; a stale chip is refused | M | big (fixed 2026-11-11, chat-one-tap-flow) |
| ~~A yes/no decision asked in prose ("Should I switch it to 36 months?")~~ | 2 | prompt rule: ask_user with options, or propose the change | S | big (fixed 2026-11-11, chat-one-tap-flow) |
| ~~A card arrives alone, with no answer to the user's question~~ | 8 | the lead sentence before a card tool is no longer hidden as an internal note | S | medium (fixed 2026-11-11, chat-one-tap-flow) |
| ~~Answered field cards keep their full height~~ | 5 | fold to "✓ Filled in · Make, Model · Undo"; click to expand | S | medium (fixed 2026-11-11, chat-one-tap-flow) |
| ~~Question cards show raw markdown (`**Loan purpose**`)~~ | 8 | inline markdown in `.card-q` | S | medium (fixed 2026-11-11, chat-one-tap-flow) |
| ~~Field cards show numbers raw (`1500000`)~~ | 8 | `Intl.NumberFormat` for numbers of 5+ digits | S | medium (fixed 2026-11-11, chat-one-tap-flow) |
| ~~A row's reason that repeats its value~~ | 8 | hidden when equal to the value | S | small (fixed 2026-11-11, chat-one-tap-flow) |
| ~~A card typed over is marked "Skipped"~~ | 8 | "Replaced by your message" | S | small (fixed 2026-11-11, chat-one-tap-flow) |
| ~~The empty chat promises suggestions it does not show; "New chat" drops the starters~~ | 7 | intro without suggestions when there are none; starters kept on New chat | S | medium (fixed 2026-11-11, chat-one-tap-flow) |
| ~~The field card shows raw error text~~ | 7 | `applyFailed`, raw text in `title` | S | medium (fixed 2026-11-11, chat-one-tap-flow) |
| The upload card still shows raw error text | 7 | the same readable message, raw text in `title` | S | small |
| Every append scrolls the log to the bottom: a long reply runs past its first line, and a reader of history is pulled down | 6 | follow the bottom only while the user is there; a new reply scrolls to its start; otherwise a "New message" pill | S | big on phones |
| Undo vanishes after 20 s, and pressing it sends a chat message that starts a whole turn | 3, 6 | revert silently and tell the agent with the next run (as the Herefront bot does); keep Undo until the next card | M | medium |
| "+" (new chat) drops the conversation at once, with no way back | 3 | a "New chat · Back" line | S | medium |
| Messages have no actions: no Copy, no Edit and resend of the last user message | 2 | Copy on a reply; Edit on the last user message | M | medium |
| The inline editor confirms with a hard-coded English "OK" | 8 | "Done" from i18n, or apply on Enter | S | small |
| ~~`theme: auto` reads the system theme once: switching the system to dark leaves the widget light~~ | 10 | listen to `prefers-color-scheme` changes | S | small (fixed 2026-11-11, chat-themes) |
| ~~Brand tokens set on the element override the dark scheme; hard-coded shadows, whites and radii cannot be themed~~ | 10 | themes with per-scheme tokens, `data-scheme` on the host, every colour and radius a token | M | big for hosts (fixed 2026-11-11, chat-themes) |
| ~~`defaultDirective` flashes with a hard-coded rgba~~ | 10 | system colours (Highlight, Canvas) on the host page | S | small (fixed 2026-11-12) |
| ~~A tap answer or an action chip fills a field on another tab without showing it; the agent's hint is never shown outside the demo form~~ | 7 | a focus directive after every fill; a hint bubble under the field in the default handling and the react-hook-form hook | S | big (fixed 2026-11-12) |
| The agent repeats the same unresolved error in most replies | 8 | name a blocker once, then a quiet "1 issue" marker | M | big |
| Number formatting groups identifiers: passport number `123456` shows as `123,456` (2026-11-12) | 8 | group digits only for amount / number fields (by role or the field spec), never for text fields that hold digits | S | big: a wrong-looking document number |
| Dates in field cards are ISO (`2015-04-02`) (2026-11-12) | 8 | `Intl.DateTimeFormat` in the chat's language for date fields ("2 Apr 2015") | S | medium |
| An 8-row field card is about 640 px tall; at 390 px the demo's chat shows about 200 px, so "Fill in" is three screens down (2026-11-12) | 1, 5, 9 | conflicts first, 4 rows then "Show N more", the action row sticky at the bottom of the log | M | big on phones |
| Each row has two text links (Edit, Show): 16 links in an 8-row card; the 15 px checkbox is the only toggle target (2026-11-12) | 9, 10 | the whole row toggles; tap the value to edit; one "show in form" icon button (44 px) | S | medium |
| A row whose value conflicts with what the form has ("you said 12 March, the form has 12 April") looks like any other row (2026-11-12) | 7 | rows with a previous value or a reason go first, with the reason in the warning colour | S | medium |
| ~~Dictation keeps running after Skip or a card answer, and dictated words stay in the composer after a chip~~ | 3, 6 | any chat action ends the dictation and drops the dictated words; typed text stays | S | medium (fixed 2026-11-12) |

## The demo form (`frontend/`)

| What is wrong | Law | How to fix | Cost | Effect |
| --- | --- | --- | --- | --- |
| ~~The page title shows the form id ("loan_application")~~ | 8 | the form's title from its pack ("Loan application") | S | small (fixed 2026-11-11, one-tap-questions) |
| After the hosted demo wakes up, the first message waits about 5 s with only dots | 6 | keep one machine running for demos; the widget now says "Still working…" after 4 s | S | medium during a demo |
| 16 px on the composer's text box is outside the type scale | 10 | keep: under 16 px iOS zooms the page on focus | - | - |

## The docs site (`site/`, 2026-11-12)

| What is wrong | Law | How to fix | Cost | Effect |
| --- | --- | --- | --- | --- |
| On a phone the live demo stacks the form above the chat; after "Fill in" the changed fields are out of view | 6 | the same bottom-sheet idea as the demo form, or a "Show the form" chip on the result line | M | medium on phones |
| The concept pages (ported diagrams) have no "On this page" list: their headings are raw HTML in fragments | 5 | move the prose of each fragment into the MDX page, keep only the SVG figures as fragments | M | small |
| Diagram SVGs keep a 640 px minimum width and scroll sideways inside their box on a phone | 10 | simplified vertical variants for narrow screens | L | small |
| ~~Answers in the widget showed fenced code as raw text~~ | 8 | code blocks with a language label and Copy (2026-11-12, docs-redesign) | S | large for the docs assistant |
| Mermaid diagrams use `<small>` for secondary labels: below the type scale at phone width | 10 | move secondary text into the edge labels, or drop it on narrow screens | S | small |
| On a phone the three page actions (Copy page, Open in Claude, Open in ChatGPT) wrap onto two lines above the content | 5 | one "Page" menu button on narrow screens | S | small |
| ~~No way to see the cards without running the demo and steering the agent to each~~ | 7 | the card gallery: every card and variant live, with its event and answer (2026-11-12, docs-card-gallery) | M | big for developers |
| The upload card shows its prompt as raw text: markdown (`**payslip**`) is not rendered, unlike question cards (2026-11-12) | 8 | the same inline markdown as `.card-q` in `uploadCard` | S | small |
| The card gallery's tiles scroll each chat to its bottom on mount, so a tall card (comparison) opens mid-way | 6 | the log-follow fix above; meanwhile the gallery could scroll each log to the card's top | S | small |

## The docs design system (`site/src/components/ui/`, 2026-11-13)

| What is wrong | Law | How to fix | Cost | Effect |
| --- | --- | --- | --- | --- |
| ~~"See the prompt" in the setup prompt: a text chevron (`\203a` / `\2304`) that sits below the text line and changes glyph instead of turning~~ | 10, 11 | the Disclosure primitive: an SVG chevron centred on the summary line, rotating 90° (fixed 2026-11-13) | S | small, seen on every visit |
| ~~Each docs component styled its own controls: four chip looks (bordered, filled, pressed grey), three menu radii (14 / 18 px), outlined vs filled pill buttons, 2 px focus rings with different offsets, `#fff` on the accent~~ | 10, 11 | one system in `site/src/components/ui/`, tokens `--fg-*`, the design-system page; the 11 components moved onto it (fixed 2026-11-13) | M | big: one look everywhere |
| ~~Hover fills stuck after a tap on phones (chips, segments, menu rows)~~ | 9 | hover rules inside `@media (hover: hover)` (fixed 2026-11-13) | S | medium on phones |
| ~~Page actions, chips and the Replay button 32-40 px on touch~~ | 9 | `--fg-h-*` heights become 44 px on `pointer: coarse` (fixed 2026-11-13) | S | medium on phones |
| ~~In dark mode the Live demo menu had the same fill as the tile under it~~ | 11 | `--fg-elevated`: menus are lighter than the page in dark, like macOS (fixed 2026-11-13) | S | small |
| ~~Ask AI's Copy said "Copied" without a check; its rows and steps used 14 px (off the scale); focus ring 2 px~~ | 10 | the Copy button's check and timing, 15 px rows, the system's 3 px ring, 44 px Copy on touch (fixed 2026-11-13) | S | small |
| The demo form on the landing (`site/src/demo/form.ts`) builds its own `df-*` controls; the select keeps the browser's arrow and the fields are not the system's | 10, 11 | build them from `ui-chip` / a Select primitive (a select with our chevron, like `frontend/src/controls.tsx`) | S | medium: the first thing people try |
| Ask AI's card CSS (`site/src/ask/docs.ts`) keeps hover rules ungated, so they can stick after a tap | 9 | `@media (hover: hover)` as in `ui.css` | S | small |
| `Stats.astro` and the concept diagrams (`arch.css`, `src/fragments/`) still use raw `--sl-*` colours and their own sizes | 10 | move to `--fg-*` tokens; Stats onto Tile / type tokens | S | small |
| Starlight's own controls (theme select with a native arrow, search button, pagination) do not match the system | 11 | override them in `theme.css` with the `--fg-*` tokens, or replace the theme select with a Segmented / Menu | M | medium: in the header of every page |

## Bigger ideas (2026-11-11)

- **Fix-it chips on errors.** When the agent reports a field error it can fix (format, range), the reply carries one intent chip ("Use +7 999 555 01 00") that applies the value with Undo.
- **Bulk start.** First message: "Fill everything I can from my profile and documents" as one card with all fields grouped by tab and one "Fill in 23 fields".
- **Phone layout.** At 390 px the form and the chat each get half the screen and the highlight lands off-screen. Make the chat a bottom sheet (peek / half / full) that drops to peek when the agent highlights a field.
- **Final review.** Before submit: a summary card by tab, "Submit" as the one confirm action, empty required fields as jump links.
- **Composer like Claude's (2026-11-13).** Done: the input grows with its text (also after server dictation), a pasted screenshot or a file dropped on the composer is attached like the paperclip's. Still to do: image attachments as thumbnails with an x (like iMessage / Claude), not a "📎 name" chip; a taller limit than 180 px on a computer (about a third of the panel).
| ~~Field card: ISO dates, passport numbers digit-grouped (123,456), the same reason on every row, small checkbox targets, actions out of reach on phones~~ | 8, 9 | values by field `kind`, one shared reason, 22 px checkbox in a 44 px row on touch, sticky actions under 520 px | S | big (fixed 2026-11-12, chat-card-kit) |
| ~~The one-script bundle carries the UI text of all seven languages~~ Fixed 2026-11-13: English built in, the rest packs loaded on first use (48.2 -> 39.4 KB, budget 42 KB) | | | | |
| ~~Native browser pickers: the date popup, time spinners, number spin buttons, select arrows, 13 px checkboxes, the default slider~~ | 10 | our calendar, time grid, number stepper, select chevron, Apple-style checkbox and slider (references/controls.md) | M | big (fixed 2026-11-12) |
| ~~Number-key hints 1-9 shown on number options ("2 1", "3 2") and on touch screens~~ | 8 | hints only with keyboard focus and never on options with digits | S | medium (fixed 2026-11-12) |
| ~~Demo form and react-hook-form example: browser date popups, spin buttons, select arrows, 13 px checkboxes, a browser file button~~ | 10 | frontend/src/controls.tsx + controls.css (copied into the example): DateInput with the widget's calendar in a popover, NumberInput with the joined stepper, Select with a chevron, Apple checkboxes, radios and file pill | M | big (fixed 2026-11-12) |
| ~~Hosts could style only a few elements (14 parts), had no per-component tokens, fixed icons, and could not put their own component in place of a message, the header, the empty chat, an error or the composer~~ | 10 | parts on every element (src/parts.ts), component tokens, options.icons, options.render slots, reactSlot | M | big for hosts (fixed 2026-11-12, chat-customization) |
| ~~The floating chat is a full-height side drawer that dims the page; no bubble launcher, no grabber on phones~~ | 11 | mode: bubble - a launcher that grows into a window with a spring, a bottom sheet with a grabber on phones, unread dot, greeting | M | big (fixed 2026-11-12, chat-bubble) |
| Reply to a quote on a real iPhone and Android: the system's Copy / Look Up menu above the selection and our capsule under it may both show; not checked on a device | 11 | check on devices; if both show, dock the capsule above the composer on touch | M | medium (found 2026-11-14) |
| ~~A swipe replies to the whole answer but sends its first 300 characters as `quote`, so the agent reads the opening as the line asked about~~ | 2 | `reply_to {message_id, whole: true}`, agreed with Owner | M | low (fixed 2026-11-14: `{message_id, whole: true}`, and the swipe goes left as in Telegram) |
| ~~A finished card faded to 72% and the long-message fade lay over cards, so "Filled in · … Undo" was hard to read~~ | 7 | the fold class is `.clamped` (never on cards), no opacity on finished cards | S | high (fixed 2026-11-14) |
