# Patterns (recipes)

Before writing a new component, check whether it is here or already in the code.
What already exists in the widget: the `h(tag, props, ...children)` helper (`src/dom.ts`); the classes `.card`, `.card-t` (small title), `.card-q` (question), `.chips` + `.chip` (`.chip.on` selected), `.acts` (the button row), `.btn.pri|sec|danger|link`, `.ok-line` (a result line, `.off` for a negative one), `.muted`, `.text-in`, `.field`, `.steps`, `.quick`, `.notice`, `.error`; renderer context `ctx.resolve(value)`, `ctx.t(key)`, `ctx.flags`. Buttons marked `data-keep` stay active after a card is answered.

## A result line with Undo (instead of a confirmation)

```ts
// The action happens at once; the card shrinks to a result line with Undo.
const line = h('div', { class: 'ok-line' }, h('i', null, '✓'), h('span', null, ctx.t('filled')),
  h('button', { class: 'btn link', type: 'button', 'data-keep': true, onclick: undo }, ctx.t('undo')))
acts.replaceWith(line)
ctx.resolve(value)
```
The text is a fact in the past tense: "Filled in", "Skipped", "Uploaded: passport.pdf". Undo stays for about 20 s, then disappears quietly.

## A confirm card (only for the irreversible)

For actions without undo that affect others: a title with the object ("Cancel the booking?"), one sentence of consequences, a red button with a verb and object ("Cancel booking"), a plain "Cancel". The red button is never the default focus.

## An intent button

One button runs a chain with no human decisions in it. A candidate: after step A the person *always* does step B. Examples here:
- a question tied to a field: tapping the option fills the field (no second card);
- "Fill in 2 of 3": applies the ticked rows through the form backend, opens the place of the last one and tells the agent;
- prefill: the app's profile becomes one card.
The label is the result, not the mechanics. If a step can fail, say which one and what to do.

## Optimistic update

Change the state at once, send the request in the background, roll back with a message on error. Good for card answers, ticks, Undo. Not for submitting an application, paying, or sending messages to people.

## Loading

- Under 150 ms: nothing. 150 ms – 1 s: the typing dots. Over 1 s with tools: the step list with a spinner on the current step.
- Reloading a thread: show the restored messages at once (no animation), then the pending card.
- A spinner only inside the button that was pressed (the button keeps its width).

## Empty states

Formula: a title (what will be here) + one sentence (why it is empty) + one action.
- An empty chat: the assistant's name · "Ask anything, or pick a suggestion." · starter chips.
- Nothing to show in a card list: say what the agent will put here.
- No access (a password, a missing key): who can give access, with no button that will not work.

## Errors

Formula: what happened · what to do · an action. "The assistant is not reachable right now. Check your connection. [Try again]". The raw server message goes only into `title` or the console. Network error, 401, 409, 429, 5xx: each has its own sentence. A field error goes under the field, when leaving it, not on every keystroke.

## Cards

A card has one job and one main action. Structure: a small title (`.card-t`) or a question (`.card-q`) → content (rows, chips, a drop zone) → `.acts` with the main action first. After it is answered or closed, it shrinks to its question and a result line; controls disappear (CSS `.card.done`, `.card.dismissed`).

## Step lists

While the agent works, each tool is a row with a spinner, then a tick. Sub-steps sit under their parent. After the run the list folds into "Steps: N ›". Tools whose result is the card that follows get no step of their own.

## Forms (inside cards)

One column, the label above the field, the right `type` / `inputmode` / `autocomplete`, `Enter` submits, the first field focused only on a computer. The submit button is always active; pressing it with errors moves focus to the first error.

## Numbers and time

Separators by locale (`toLocaleString`), `tabular-nums` in counters, plurals by rule, never "1 steps". Relative time when close ("5 min ago"), absolute when far.

## Motion

Animate only what explains: where a card came from, which row changed, that a step finished. Durations and curves: `tokens.md`. A press: `scale(0.98)`. Everything off with `prefers-reduced-motion`.
