---
name: ui-craft
description: The project's UI/UX standard, anchored on Apple: every component looks and behaves like its iOS / macOS counterpart, in Apple's spirit on every surface (the docs site included); minimal and simple, with Telegram's speed and Revolut's one-tap flows. One main action per screen, complex tasks in one tap, Undo instead of confirmations, instant response, designed empty and error states. Load BEFORE any interface change (the <agui-chat> widget in packages/agui-chat, the demo form in frontend/, the docs site in site/, examples/, button and hint texts, card renderers); when designing a new card, screen or flow; and for audits ("check the UI", "make it simpler or nicer", "UX review", "why is this awkward").
---

# UI Craft: how we build interfaces

An interface is not a set of features. It is **the shortest path from what a person wants to the result**. A good screen is almost empty: it has what is needed now and one obvious button. Everything else is one step deeper.

Adapted from the Cheese project's standard (web_search_company_without_web, `.claude/skills/ui-craft`) for formguide's surfaces.

The references, and what we learn from each:

| | What we learn |
| --- | --- |
| **Apple** (the anchor) | Every component like its Apple counterpart, and Apple's spirit: clarity, deference to the content, depth through layers. Quiet and hierarchy: a large title, lots of air, one accent colour, the system font, properties instead of settings. A gesture or action answers at once, and animation explains where things came from. |
| **Telegram** | Speed and density without noise: everything is instant, optimistic, tolerant of a bad network. Power gestures for experts, a plain tap for everyone. It never asks for no reason. |
| **Revolut** | The complex in one tap: a transfer, freezing a card, splitting a bill are one button, with the details filled in by defaults. The main screen shows what matters now, not a menu. Numbers are large and clear. |

## Apple experience (always)

**Apple is our anchor.** Every component looks and behaves like its counterpart in iOS / macOS, so that someone with an iPhone recognises it and knows what it does without a hint; where Apple has nothing similar, we design by the same principles (clarity, deference to the content, depth, one obvious action, an answer at once). Models per surface: the chat is **iMessage** (an iOS sheet on phones), cards are **iOS grouped lists and sheets**, the demo form is **macOS / iOS Settings**, the docs are **developer.apple.com**. Component by component, with our classes: `references/apple-components.md`; the controls themselves (fields, steppers, pickers, calendar): `references/controls.md`.


Every component, in the widget and on every page we ship, should feel like Apple made it: soft filled fields, joined controls (a number field's stepper sits on its right edge, full height, with chevrons), our own chevrons instead of browser arrows, pill buttons, 44 px targets on touch, quiet 150-200 ms transitions, light and dark. Native behaviour stays (keyboards, pickers, accessibility); the browser's look goes. Control by control: `references/controls.md`. If a control looks like a default browser widget, it is not done.

## The Apple spirit (everywhere, not only controls)

Controls are the letter; this is the spirit. It applies to every surface we ship: the widget, every card, the demo form, the examples, **and every page of the docs site** (guides, reference, landing, gallery).

- **Clarity.** One idea per screen, section or card, said in its headline. Large, confident type with a clear hierarchy (a statement headline, a quiet one-line subhead, then the thing itself). If a heading needs a second line to explain it, the section does too much.
- **Deference.** The content is the interface: the real chat, the real card, the real code. Chrome (borders, boxes, badges, labels) recedes; whitespace and soft fills separate things instead of lines.
- **Show, then tell.** Lead with the real thing working (a live card, a copyable snippet that runs), then one or two sentences of why. Never a wall of text before the first example.
- **Depth with restraint.** Soft layers (a tile on the page, a card in the tile), gentle radial light, one shadow style; no gradients for decoration, no more than one accent colour.
- **Every detail finished.** Aligned edges, consistent radii, no orphaned words in headlines, no raw ids or JSON shown to end users, empty and error states as considered as the happy path, light and dark equally good.
- **Calm motion.** Things fade and move 150-200 ms to show where they came from; nothing bounces for fun; reduced motion respected.
- **Plain, warm words.** Short sentences, verbs on buttons, no jargon for users; for developers, the exact name of the type or key, once, with a link.

**The docs site has one component system:** `site/src/components/ui/` (Button, Copy button, Chips, Segmented control, Disclosure, Tile, Callout, Link card, Menu, Range, Swatches, Code panel, Badge, Summary), styled from the `--fg-*` tokens in `site/src/styles/theme.css` and shown live on **Reference → Design system** (`site/src/content/docs/reference/design-system.mdx`). Docs UI uses only these; a new pattern is added there first (component, `ui.css` block, specimen on the page), then used. Component files keep only layout. Ask AI's cards (`site/src/ask/docs.ts`, shadow DOM) follow the same look through `--agui-*` tokens. Rules, the Apple counterpart of each primitive and how to add one: `references/docs-components.md`.

On the docs site this means: a page opens with its one-line promise and the example; tiles (`border-radius` 20-28 px, soft fill) for galleries and choices; tabs for variants instead of repeated blocks; navigation always one tap away (every page keeps the sidebar; no page is a dead end). Check against Apple's product and developer pages: if ours looks busier, remove until it does not.

## Before the first line of code: a mini-brief (required)

Answer in writing, in the reply to the user or in the OpenSpec change's `design.md`, in 5 lines:

1. **Who and why.** A loan applicant fills the form with the assistant's help / a barbershop guest books a slot / a manager uploads the business documents / a developer embeds `<agui-chat>`.
2. **The screen's or card's main action**: exactly one. Only it is the filled button (`.btn.pri`).
3. **The tap ladder:** how many taps or screens to the goal now → how many after. The goal is at least one fewer.
4. **States:** empty, loading, error, partial, no access, too many, offline: what each shows.
5. **Phone:** what changes at 390 px (the main action in the bottom third, under the thumb).

If you cannot name one main action, the screen or card does too much. Split it, or hide the secondary.

## The eleven laws

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
11. **Like Apple.** Every component looks and behaves like its counterpart at Apple (iOS / macOS): the same shape, the same press, swipe and keyboard behaviour, the same words for the same action. Before you ship a component, answer: how does Apple do it, what happens on tap, hold, swipe and key, and what did I do differently, and why. Reference: `references/apple-components.md`.

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
- Browser-default chrome left in place: spin buttons on number inputs, native select arrows next to our styles, bare 13 px checkboxes as the only tap target (see `references/controls.md`).

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
| The chat widget `<agui-chat>` | `packages/agui-chat/src/element.ts`, `styles.ts`, `formguide/cards.ts`, `i18n.ts` | end users of any host app; phone and computer | 7 languages: English in `i18n.ts` (`STRINGS`, `FG_STRINGS`), the others in `src/lang/<lang>.json` packs (every English key in every pack) | `--agui-*` on `:host`, light and dark |
| The demo form and its page | `frontend/src/App.tsx`, `Form.tsx`, `index.css` | someone trying formguide; mostly computer | en | the demo's own `:root` variables |
| The HTML example | `examples/widget-html/index.html` | developers trying the widget | en | its own `:root` |
| The docs site | `site/` (Astro Starlight): `src/styles/theme.css`, the design system `src/components/ui/` (every docs control), `src/components/` (the live demo `LiveDemo.astro` + `src/demo/`), pages in `src/content/docs/`, diagrams in `src/fragments/` | developers and managers; phone and computer | en | `--fg-*` (built on Starlight's `--sl-*` with formguide's accent) in `theme.css`; diagrams map them in `arch.css` |

The widget is the product: host apps restyle it only through tokens and `::part`, so everything visual in it must come from tokens. New text in the widget goes into English (`i18n.ts`, `formguide/i18n.ts`) and into every pack in `src/lang/*.json` (non-ASCII as `\u` escapes, see CLAUDE.md); `test/langs.test.ts` fails when a pack misses a key.
