# Design

## Mini-brief (ui-craft)
1. **Who and why:** a person filling a form wants help without leaving the page.
2. **Main action:** tap the launcher; the chat grows out of it.
3. **Ladder:** the same one tap as the drawer, but the page stays visible and usable next to the window.
4. **States:** closed (launcher, maybe a greeting), opening (spring), open, closing (quick shrink back), unread (dot + bounce), reduced motion (fade only).
5. **Phone:** under 520 px the window is a bottom sheet with a grabber, the page dimmed; the launcher stays at the thumb.

## Motion (Apple-like spring)
- Open: the window scales from .18 to 1 with transform-origin at the launcher, its radius morphs from round to 24 px, opacity 0 to 1, 520 ms `cubic-bezier(.34, 1.4, .5, 1)` (a small overshoot); the header, log and composer rise 8 px and fade in at 120 / 180 / 240 ms.
- Close: back to the launcher in 220 ms `cubic-bezier(.4, 0, 1, 1)`, no overshoot.
- `motion: gentle`: no overshoot, 320 ms; `none` and `prefers-reduced-motion`: fades only.

## showCard
`showCard(payload)` gives the card a `card_id` when it has none and renders it through the same renderer registry as interrupts. Its answer resolves the returned promise instead of resuming a run.
