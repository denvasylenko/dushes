---
name: ui-craft
description: The project's UI/UX standard, minimal and simple at the level of Apple, Telegram and Revolut. One main action per screen, complex tasks in one tap, Undo instead of confirmations, instant response, designed empty and error states. Load BEFORE any interface change (the <agui-chat> widget in packages/agui-chat, the demo form in frontend/, the docs site in site/, examples/, button and hint texts, card renderers); when designing a new card, screen or flow; and for audits ("check the UI", "make it simpler or nicer", "UX review", "why is this awkward").
---

# UI Craft: how we build interfaces

An interface is not a set of features. It is **the shortest path from what a person wants to the result**. A good screen is almost empty: it has what is needed now and one obvious button. Everything else is one step deeper.

Adapted from the Cheese project's standard (web_search_company_without_web, `.claude/skills/ui-craft`) for formguide's surfaces.

The references, and what we learn from each:

| | What we learn |
| --- | --- |
| **Apple** | Quiet and hierarchy: a large title, lots of air, one accent colour, the system font, properties instead of settings. A gesture or action answers at once, and animation explains where things came from. |
| **Telegram** | Speed and density without noise: everything is instant, optimistic, tolerant of a bad network. Power gestures for experts, a plain tap for everyone. It never asks for no reason. |
| **Revolut** | The complex in one tap: a transfer, freezing a card, splitting a bill are one button, with the details filled in by defaults. The main screen shows what matters now, not a menu. Numbers are large and clear. |

## Before the first line of code: a mini-brief (required)

Answer in writing, in the reply to the user or in the OpenSpec change's `design.md`, in 5 lines:

1. **Who and why.** A loan applicant fills the form with the assistant's help / a barbershop guest books a slot / a manager uploads the business documents / a developer embeds `<agui-chat>`.
2. **The screen's or card's main action**: exactly one. Only it is the filled button (`.btn.pri`).
3. **The tap ladder:** how many taps or screens to the goal now → how many after. The goal is at least one fewer.
4. **States:** empty, loading, error, partial, no access, too many, offline: what each shows.
5. **Phone:** what changes at 390 px (the main action in the bottom third, under the thumb).

If you cannot name one main action, the screen or card does too much. Split it, or hide the secondary.

## The ten laws

In detail, with examples from our code: `references/principles.md`.

1. **One main action.** One filled button in view. Secondary actions are grey, tertiary ones are links or under "More".
2. **Complex → one tap.** Glue steps into an *intent button*. A question tied to a field fills the field when answered; it does not need a second card. The user says *what*; the system decides *how*.
3. **Do, don't ask.** The action happens at once, with "Undo" next to its result. Confirm only what cannot be undone and affects others (submitting an application, cancelling a booking), and then with a card that names the action on its button. `window.confirm/alert/prompt`: never.
4. **Smart defaults.** The last choice, the language and the locale from context, values the app already knows (prefill), the field the user is looking at. An empty field we could have filled is our oversight.
5. **Progressive disclosure.** 80% of tasks on the surface; the rest behind "More", a link, or a collapsed list (tool steps collapse into "Steps: 3"). Rare and dangerous things go deepest.
6. **Instant.** A response to a tap within 100 ms (optimistic update). Show an indicator only after 150 ms. While reloading, keep the old content and add a thin hint, not a full-screen spinner. Nothing jumps: space for images and numbers is reserved.
7. **Every state is designed.** Empty = what will appear here + one action. Error = what happened in human words + what to do + "Try again". The server's raw error text is never shown.
8. **Words are interface too.** A verb and an object on a button ("Fill in 2 fields", not "OK"). No jargon (jsx_hash, interrupt, AG-UI, SSE are not for users). Numbers with separators and correct plurals. Rules: `references/copy.md`.
9. **Fingers and keyboard.** Tap targets ≥ 44×44 on a phone; nothing important only on hover. On a computer: `Esc` closes, `Enter` confirms, number keys pick options, `Tab` moves in a sensible order.
10. **Quiet and system.** Only tokens (`--agui-*` in `packages/agui-chat/src/styles.ts`), one type scale, one spacing scale, one radius scale, one accent colour, motion with meaning, `prefers-reduced-motion` respected. Scales: `references/tokens.md`.

## What we never do (hard rules)

- `window.confirm`, `alert`, `prompt`; a modal on top of a modal; a card that only repeats a choice the user just made.
- A colour as a hex or rgba in new CSS rules or in renderers: only `var(--agui-…)` in the widget (the demo's own `var(--…)`). Inline `style` only for values from data (a progress width, a percentage).
- A new font size or radius outside the scale (`12.5px`, `13.5px`, `9px` and the like).
- A disabled button with no explanation of why and how to fix it.
- An action that exists only on hover: a phone has no hover.
- `autofocus` on a field when, on a phone, it would open the keyboard over the content.
- A hint or onboarding that comes back after it was closed.
- Horizontal page scroll at 390 px; text cut off without a `title` or a way to expand it.
- Two buttons with the same meaning, or two items with the same name.
- A "Saving…" indicator flashing on every action. Success is silent or a short fact; only errors stand out.

## How to work

**A new card, screen or flow** → mini-brief → find a ready pattern in `references/patterns.md` (a result line with Undo, a confirm card, an intent button, an empty state, a step list) → reuse the widget's classes (`.card`, `.card-t`, `.card-q`, `.chips`/`.chip`, `.acts`, `.btn pri|sec|danger|link`, `.ok-line`, `.muted`) and the `h()` helper; do not invent new ones → check.

**Changing existing UI** → first read the neighbouring code and repeat its techniques. Fix violations of the laws only in the area you touch; list the rest in the report and in `references/audit.md`.

**Check (always, before "done")**, see `references/review.md`:
- in the browser at 390×844 and 1280×800, light and dark theme;
- keyboard only: Tab order, visible focus, `Esc`, number keys on question cards;
- a slow network and an empty thread (empty states, the restored chat);
- the tap ladder matches the brief;
- a screenshot to the user when the look changed.

**Audit ("check the UX")** → go through `references/review.md` screen by screen and give a table: *surface · what is wrong · which law · how to fix · cost S/M/L · effect*, quick wins first. Known debt and big ideas: `references/audit.md` (do not repeat what is found; update the file).

## Map of surfaces

| Surface | Files | Who | Language | Tokens |
| --- | --- | --- | --- | --- |
| The chat widget `<agui-chat>` | `packages/agui-chat/src/element.ts`, `styles.ts`, `formguide/cards.ts`, `i18n.ts` | end users of any host app; phone and computer | 7 languages (`STRINGS`, `FG_STRINGS`; every key in every language) | `--agui-*` on `:host`, light and dark |
| The demo form and its page | `frontend/src/App.tsx`, `Form.tsx`, `index.css` | someone trying formguide; mostly computer | en | the demo's own `:root` variables |
| The HTML example | `examples/widget-html/index.html` | developers trying the widget | en | its own `:root` |
| The docs site | `site/` (Astro Starlight): `src/styles/theme.css`, `src/components/` (the live demo `LiveDemo.astro` + `src/demo/`), pages in `src/content/docs/`, diagrams in `src/fragments/` | developers and managers; phone and computer | en | Starlight's `--sl-*` with formguide's accent in `theme.css`; diagrams map them in `arch.css` |

The widget is the product: host apps restyle it only through tokens and `::part`, so everything visual in it must come from tokens. New text in the widget goes into the generated i18n files in all seven languages (non-ASCII as `\u` escapes, see CLAUDE.md).
