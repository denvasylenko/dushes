# Controls, the Apple way

Every control in the widget, the demo form and the examples should feel like iOS / macOS: soft, roomy, quiet, and obvious to a thumb. The browser's own chrome (spin buttons, select arrows, checkbox squares from 2005) is replaced or restyled; the behaviour (keyboard, accessibility, native pickers) is kept.

For host pages (the demo form, the examples): `frontend/src/controls.tsx` and `controls.css` (DateInput, NumberInput, Select, checkbox, radio, file), styled through `--c-*` variables each page maps. The widget's implementation is the reference: `packages/agui-chat/src/styles.ts` (inputs, `.num`, `.sel`, `.chip`, `.opt`, `.btn`) and `src/dom.ts` (`numberBox`, `selectBox`).

## The rules

| Control | Looks like | Never |
| --- | --- | --- |
| Text field | a soft filled field (`--agui-soft`), no visible border at rest, radius `--agui-radius-sm`, 44 px tall, 16 px text (iOS does not zoom), padding 10 x 14. Focus: the background turns to `--agui-bg`, a 1 px accent border and a 3 px soft accent ring | a grey 1 px box on white; a placeholder that repeats the label above it |
| Number field | the field plus a stepper joined to its right edge: two halves on the full height, a hairline between them and on the left, chevrons up and down (12 px, 1.8 stroke), 38 px wide (44 px on touch); arrow keys step | the browser's tiny spin buttons; a stepper floating inside with its own rounded box |
| Short range (under 10 steps) | a stepper with round 36 px (44 px touch) minus and plus around the value, the result line next to it, then "Set 5 years" | a slider for 3 values |
| Long range | a slider in the accent colour with the value and the live result above the action | a number box for a range the user explores |
| Select | the same soft field, the native arrow hidden, our own chevron 16 px from the right edge | the native arrow next to a custom one |
| Long list (more than 12) | a search field and the likely options first, filtering as you type | a select with 200 options |
| Choice of 2-5 | chips (pill, 1 px hairline, 44 px on touch) or two-line options when there is a description | radio buttons in a column |
| Yes / no | two chips, or a switch in a form | a checkbox for a question |
| Checkbox in a list row | the whole row toggles it; 22 px box in a 44 px row on touch; accent colour | a 13 px box as the only tap target |
| Date | quick picks first (Today, Tomorrow, the next days) when the range is ahead; our calendar (`src/formguide/calendar.ts`): weekdays of the chat's language, round days, the accent on the chosen day, a link-coloured today, the title opens years then months, min / max respected, arrow keys move; a past date (a birthday, a founding date) opens the calendar right away on the right month | the browser's date popup; a bare `dd.mm.yyyy` box |
| Time | free slots as chips, else a grid every 30 minutes within min / max | the browser's time spinner |
| Range slider | a 4 px soft track, the filled part in the accent, a 26 px white knob (`--agui-knob`) with a soft shadow | the browser's default slider |
| Buttons | one filled pill (`.btn.pri`) per card, secondary outlined pills, tertiary text links; 44 px on touch | two filled buttons; square buttons |

## Feel

- **Soft, not boxed.** Fill and radius separate controls; hairlines (`--agui-line`) only divide.
- **Joined, not floating.** Parts of one control (a field and its stepper, a segmented control) share one outline and one radius.
- **Thumb first.** 44 px targets on touch screens, the main action in the bottom third, nothing only on hover.
- **Quiet motion.** 150-200 ms colour and background transitions; a chevron rotates when something opens; nothing moves with reduced motion.
- **Native where it helps.** Keep native date pickers, keyboards (`inputmode`), autofill and screen-reader roles; replace only the look.
- **Check both themes.** Every control in light and dark, at 390 px and desktop, before "done".
