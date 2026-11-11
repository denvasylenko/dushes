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

## The demo form (`frontend/`)

| What is wrong | Law | How to fix | Cost | Effect |
| --- | --- | --- | --- | --- |
| ~~The page title shows the form id ("loan_application")~~ | 8 | the form's title from its pack ("Loan application") | S | small (fixed 2026-11-11, one-tap-questions) |
| After the hosted demo wakes up, the first message waits about 5 s with only dots | 6 | keep one machine running for demos; the widget now says "Still working…" after 4 s | S | medium during a demo |
| 16 px on the composer's text box is outside the type scale | 10 | keep: under 16 px iOS zooms the page on focus | - | - |

## Bigger ideas (2026-11-11)

- **Fix-it chips on errors.** When the agent reports a field error it can fix (format, range), the reply carries one intent chip ("Use +7 999 555 01 00") that applies the value with Undo.
- **Bulk start.** First message: "Fill everything I can from my profile and documents" as one card with all fields grouped by tab and one "Fill in 23 fields".
- **Phone layout.** At 390 px the form and the chat each get half the screen and the highlight lands off-screen. Make the chat a bottom sheet (peek / half / full) that drops to peek when the agent highlights a field.
- **Final review.** Before submit: a summary card by tab, "Submit" as the one confirm action, empty required fields as jump links.
