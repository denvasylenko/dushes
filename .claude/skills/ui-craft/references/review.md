# Check and audit

## Quick self-check (after every UI change)

- [ ] The mini-brief is done: one main action, the tap ladder did not grow.
- [ ] No `confirm/alert/prompt`, no hex colours in renderers or new CSS rules, no font sizes or radii off the scale.
- [ ] Every state: empty, loading (> 150 ms), error with "Try again", no access, too many, after a reload.
- [ ] Text: a verb and an object, no jargon, correct plurals, all seven widget languages.
- [ ] 390×844: no horizontal scroll, targets ≥ 44, the main action under the thumb, the keyboard does not cover the field.
- [ ] 1280×800: lines not stretched across the screen (≤ about 70 characters), no empty holes.
- [ ] Light and dark theme: contrast, shadows, nothing glaring.
- [ ] Keyboard: sensible Tab order, visible focus only for keyboard focus, `Esc` closes, `Enter` confirms, number keys on question cards.
- [ ] `prefers-reduced-motion`: nothing moves.
- [ ] Nothing important only on hover.

## How to check in the browser

The demo server: `cd backend && uv run uvicorn demo.app:app --port 8000 --reload --reload-dir formguide --reload-dir demo`, after building the widget (`cd packages/agui-chat && npm run build`) and the demo (`cd frontend && npm run build`).

- The widget alone, every card at once, without a model: on `http://localhost:8000/examples/widget/`, create several `<agui-chat mode="inline">` elements and give each `chat.agent = {run(){...}}`, an object whose `run()` emits a scripted list of AG-UI events (text, tool steps, each interrupt type). Then screenshot them in `theme: 'light'` and `'dark'`.
- The built-in browser: `resize_window` mobile / desktop, `colorScheme` light / dark, screenshots before and after. Animations can be mid-way in a hidden pane: wait a second before judging faint cards.
- The widget's own tests: `cd packages/agui-chat && npm test` (behaviour and speed budgets).
- Reset the window size to `desktop` afterwards.

## Audit: scoring a surface on the ten laws

Each law 0–2 (0 broken, 1 partly, 2 exemplary), out of 20. ≥ 17: the level of the references; 12–16: good, with quick wins; < 12: redesign (a new mini-brief).

Report format:

| Surface | What is wrong | Law | How to fix | Cost | Effect |
| --- | --- | --- | --- | --- | --- |

Order: quick wins first (S, big effect), then the large ones. For each large one, the tap ladder before and after. Record findings in `audit.md` with a date; strike out what is fixed.

## UX numbers worth measuring

- Taps from the first message to a filled field.
- How often a card is rejected or undone (many → the agent proposes the wrong thing, or the card says it badly).
- Time to first token and turn time (`run_stats`, see docs/observability.md).
- Share of answers given by tapping (chips, cards) versus typing.
