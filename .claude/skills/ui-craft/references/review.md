# Check and audit

## Quick self-check (after every UI change)

- [ ] The mini-brief is done: one main action, the tap ladder did not grow.
- [ ] Like Apple: each component matches its iOS / macOS counterpart in look and behaviour (`apple-components.md`); no browser chrome left (`controls.md`).
- [ ] No `confirm/alert/prompt`, no hex colours in renderers or new CSS rules, no font sizes or radii off the scale.
- [ ] Every state: empty, loading (> 150 ms), error with "Try again", no access, too many, after a reload.
- [ ] Text: a verb and an object, no jargon, correct plurals, all seven widget languages.
- [ ] 390×844: no horizontal scroll, targets ≥ 44, the main action under the thumb, the keyboard does not cover the field.
- [ ] 1280×800: lines not stretched across the screen (≤ about 70 characters), no empty holes.
- [ ] Light and dark theme: contrast, shadows, nothing glaring.
- [ ] Keyboard: sensible Tab order, visible focus only for keyboard focus, `Esc` closes, `Enter` confirms, number keys on question cards.
- [ ] `prefers-reduced-motion`: nothing moves.
- [ ] Nothing important only on hover.
- [ ] No layout shift: nothing above the eyes moves; new content below or in a pinned zone; status is one line changing in place;
      heights ease over ~200 ms; auto-scroll only when the reader is already at the bottom (check: scroll up while an answer streams).

## Small things: polish against Apple (Head of Design, 14.11.2026, after the owner's chat screenshot)

Go through it at 390 and 1280, light and dark, with short and long text, in every state (running, done, error).

**Rhythm and spacing**
- [ ] Spacing only from the scale 4/8/12/16/24/32. Tighter inside one group, clearly more between groups: in the chat, text → card 8, turn → turn 20–24.
- [ ] The actions row (copy, reply) sits 8 below what it belongs to, aligned to the content's left edge, not the card's.
- [ ] Nothing touches an edge: a card's inner padding ≥ 12 (phone) / 16 (computer), the same on every side.

**Alignment**
- [ ] An icon next to text is centred on the line box (`align-items: center`, icon 1–1.25 em), not on the block's top. A tick, a chevron and text in one line share one axis.
- [ ] Left edges line up: a card's title, its text, its caption and the actions row start on one vertical.
- [ ] Numbers and times use `tabular-nums`, so they do not jump when digits change.

**Overlaps**
- [ ] Nothing covers the chat's text: tooltips, floating buttons, "↓", the keyboard. A tooltip appears beside its control and never over the next lines; on a phone there is none.
- [ ] Pinned areas (header, composer, suggestions) are set apart from the log: its last line is fully visible above them.
- [ ] A layer on top (sheet, menu) dims or blurs what is behind; never two layers over one place.

**Wrapping and cropping**
- [ ] Text is never cut silently. A long word or link wraps (`overflow-wrap: anywhere`); code scrolls sideways inside its own block with its own padding, never clipped by the card.
- [ ] An ellipsis only where the full text is near or one tap away; single lines only for captions and names.
- [ ] Text ≤ ~70 characters wide on a computer; on a phone nothing is wider than the screen (no sideways page scroll).

**States and motion**
- [ ] "Running → done" changes in place at the same height; an icon does not jump when the text changes.
- [ ] Appearing takes 150–250 ms and moves no neighbours; with reduced motion, at once.
- [ ] Pressed, hover and focus are visible and the same on elements of one kind.

## How to check in the browser

The demo server: `cd backend && uv run uvicorn demo.app:app --port 8000 --reload --reload-dir formguide --reload-dir demo`, after building the widget (`cd packages/agui-chat && npm run build`) and the demo (`cd frontend && npm run build`).

- The widget alone, every card at once, without a model: on `http://localhost:8000/examples/widget/`, create several `<agui-chat mode="inline">` elements and give each `chat.agent = {run(){...}}`, an object whose `run()` emits a scripted list of AG-UI events (text, tool steps, each interrupt type). Then screenshot them in `theme: 'light'` and `'dark'`.
- The built-in browser: `resize_window` mobile / desktop, `colorScheme` light / dark, screenshots before and after. Animations can be mid-way in a hidden pane: wait a second before judging faint cards.
- The widget's own tests: `cd packages/agui-chat && npm test` (behaviour and speed budgets).
- Reset the window size to `desktop` afterwards.

## Audit: scoring a surface on the twelve laws

Each law 0–2 (0 broken, 1 partly, 2 exemplary), out of 22. ≥ 19: the level of the references; 13–18: good, with quick wins; < 13: redesign (a new mini-brief). Law 11 (like Apple) is checked against `apple-components.md`.

Report format:

| Surface | What is wrong | Law | How to fix | Cost | Effect |
| --- | --- | --- | --- | --- | --- |

Order: quick wins first (S, big effect), then the large ones. For each large one, the tap ladder before and after. Record findings in `audit.md` with a date; strike out what is fixed.

## UX numbers worth measuring

- Taps from the first message to a filled field.
- How often a card is rejected or undone (many → the agent proposes the wrong thing, or the card says it badly).
- Time to first token and turn time (`run_stats`, see site/src/content/docs/guides/observability.md).
- Share of answers given by tapping (chips, cards) versus typing.
