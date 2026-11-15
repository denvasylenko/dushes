# What the owner expects from design (summary, 12–15 Nov 2026)

An English copy of the summary the CTO put together from the owner's decisions and remarks; the original lives in the
Herefront project's `ui-craft` skill (`references/owner-brief.md`). The owner's words are in quotes, translated from
Russian. Where this file and the rest of the skill disagree, this file is right; only the owner changes it (through the
CPO or the CTO). Read it before any new screen, card or flow.

The original's section on Herefront's current focus list is left out: it does not apply to this package.

## 1. The bar

"It has to be done like Apple, Revolut, Telegram." The product should make people say "wow", not "fine". The owner of a
café or a barbershop lives in WhatsApp and Instagram: a screen that is harder than those is a bad screen. The final check
of any path: five real café or barbershop owners get through it without a hint.

## 2. Which reference answers for what

| Reference | What we take | What we do not take |
| --- | --- | --- |
| **Revolut** | **The look of the owner's screens** (cabinet, app, settings, connections): large cards, bold type, the main number on top, colour and icons, "what matters now", the complex in one tap, fast onboarding | feature overload, pushy selling |
| **Apple** | **How components behave and their proportions** (press, swipe, sheet, focus, motion): `apple-components.md` | screens that look "like iPhone Settings": grey inset lists on main screens |
| **Telegram** | Speed and response: instant, optimistic, no waiting | — |

About a screen in the style of iOS Settings the owner said: "this is not Revolut… this is some nonsense"; about a header
and tabs in Revolut's spirit: "now that is better". A Settings-style list is acceptable only on deep, secondary screens.

## 3. Hard requirements

1. **One main action per screen.** Everything else is one step deeper.
2. **Nothing jumps** (the "no layout shift" law): what is above the eye does not move; the status is one live line; hints
   sit above the composer; new things appear in their own place. A flash on loading or saving is a defect.
3. **Show, don't tell:** the assistant leads to the field and highlights it; it does not explain in words where it is.
4. **What is done gets quieter by its shape, not by opacity.**
5. **Every state** is drawn before the code: empty, loading, error, no access, offline, too many.
6. **"Undo" instead of confirmations**; what cannot be undone gets one confirmation sheet.
7. **The cabinet in a phone browser and the iOS app are "one to one":** one scheme, and a screen is accepted as a pair of
   shots, web at 390 px and iOS, side by side. (A Herefront rule; for this package it means the widget looks and behaves
   the same in both.)
8. **We do not take the browser's shortcuts** (⌘D, ⌘U and the like).
9. **The chat is one everywhere:** this package's `<agui-chat>`; nobody draws their own chat window. The reference for the
   composer and the message queue is Claude.
10. **Internal terms and technical words are never shown to the user.** Texts are short and human (`copy.md`, the
    `ux-writer` subagent), in the user's language. (The original also holds a Herefront rule about when a site's term is
    named; it does not apply here.)
11. **No invented data on a screen:** prices, hours, phone numbers are real or clearly marked as an example.
12. **A number in a report or a sketch is a measured one.** "A site builds in 30–60 seconds" was written without measuring
    and produced a task nobody needed (15 Nov: the build takes milliseconds). Not measured? Say so: "not measured".

## 4. What the owner was unhappy with (do not repeat)

- A screen that flashes or redraws after "Save"; steps and hints that push the content.
- A floating button that covers the site's main button; a bottom bar that covers content.
- The cabinet on a phone overloaded; the main thing not visible without scrolling.
- A screen "like iOS Settings" where Revolut-style cards were expected.
- A docs reference with cut-off lines and empty spaces; a needed page ("Installation") that cannot be found in the navigation.
- Plurals and small texts: "1 ospiti", "Mancano 1 passi".
- A decision of his changed without asking (the tabs in the docs header were removed).

## 5. How to show work to the owner

- Not a description but a **picture**: a shot at 390 and 1280, light and dark; for mobile, a web / iOS pair.
- Anything arguable: **2–3 variants side by side** on one sheet with a recommendation, not one "right" answer.
- His decisions are never changed silently: to do it differently, bring the reasons to the CPO.
- "Done" = the shots + what was checked (`review.md`) + what was not.

## 6. Spending discipline (design is the most expensive work, because of the shots)

- Take tasks **as a batch** per screen or path, not one fix at a time.
- The browser check is **one full pass at the end** (390 / 1280, both schemes), not after every step; spot shots along the way.
- The `ux-review`, `ui-review` and `ux-writer` subagents are called before "done", for the whole path, not for every detail.
- Design does not start paid model runs.
