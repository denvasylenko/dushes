# Design

## Mini-brief (ui-craft)

1. **Who and why.** A developer evaluating or integrating formguide: first sees what it does, then finds the integration path for their stack, then looks up an exact key or payload.
2. **Main action.** On the landing page: "Get started" (the one filled button). On a guide page: copy the next code block.
3. **Tap ladder.** Today: README → find the GitHub Pages link → one long page → scroll. After: landing → "Get started" → a running agent in 3 commands; any key or event is one search away (`/` or Cmd+K).
4. **States.** The demo: idle (starter chips), streaming, a card waiting, filled with Undo, "Replay" at the end; with JavaScript off the demo area shows a static screenshot-like description and a link to the guide. Search: empty query shows nothing, no results says so.
5. **Phone.** The demo stacks: the form above, the chat below at full width; the hero button stays in the first screen; tables scroll inside their own box, never the page.

## Decisions

- **Starlight** over a hand-written generator: search (Pagefind), navigation, themes, accessibility and MDX come for free; custom landing via a splash template and our own components.
- **Content as MDX in `site/src/content/docs/`.** The old `docs/*.md` content is moved, not duplicated.
- **Specs at build time**: `site/scripts/specs.mjs` (run by `npm run dev` and `npm run build`) renders `../openspec/specs/*/spec.md` into one page per capability plus an index, so specs never drift; the output is git-ignored.
- **The scripted agent** implements the widget's `AgentLike` (`run(input) → subscribe`) and picks a script by the user's text, a card answer (`forwardedProps.command.resume`) or a starter. The form is built with `schemaForm` from the widget package, so "fill" and "Undo" go through the same code as a real integration.
- **The widget** is imported from `packages/agui-chat/src/` directly (Vite compiles the TypeScript), so the demo always runs the current widget with no separate build step.
- **Diagrams** stay inline SVG, moved from the architecture page into Astro components, themed with Starlight's CSS variables.
- **Theme**: Starlight's tokens with formguide's accent (teal `#0d6e66` family), one accent, the system font stack for text, a mono for code.
